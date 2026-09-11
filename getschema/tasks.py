from __future__ import absolute_import
import json
import logging
from django.conf import settings
from django.utils import timezone
import traceback

import urllib
from getschema.models import Schema, Object, Field, Debug, StandardObject
from django.conf import settings
from . import utils
import requests
from celery import shared_task
import datetime


def get_standard_objects():
    standard_objects = []
    for standard_object in StandardObject.objects.all():
        standard_objects.append(standard_object.name)
    return standard_objects


@shared_task
def get_objects_and_fields(schema_id): 

    schema = Schema.objects.get(pk=schema_id)
    instance_url = schema.instance_url
    access_token = utils.decrypt_str(schema.access_token)
    api_version = schema.api_version
    if api_version is None or len(api_version) < 1:
        api_version = str(settings.SALESFORCE_API_VERSION) + '.0'

    # Update to running
    schema.status = 'Running'
    schema.save()

    # List of standard objects to include
    standard_objects = get_standard_objects()

    headers = {
        'Authorization': 'Bearer ' + access_token, 
        'content-type': 'application/json'
    }

    # Describe all sObjects
    all_objects = requests.get(
        instance_url + '/services/data/v%s/sobjects/' % api_version, 
        headers=headers
    )

    entity_id_mapping = {}
    entity_id_mapping_rev = {}
    if schema.include_field_description:
        managed_where_exclude = ''
        if not schema.include_managed_objects:
            managed_where_exclude = ' AND NamespacePrefix = NULL'

        description_object_query = f"SELECT EntityDefinitionId FROM CustomField WHERE NamespacePrefix = NULL AND Description != NULL{managed_where_exclude} GROUP BY EntityDefinitionId ORDER BY EntityDefinitionId"
        description_object_ids_req = requests.get(
            f"{instance_url}/services/data/v{api_version}/tooling/query/?q=" + urllib.parse.quote(description_object_query, safe=''),
            headers=headers
        )

        entity_definition_id_list = []

        if description_object_ids_req.ok:
            description_object_ids = description_object_ids_req.json()
            if 'records' in description_object_ids:
                for current_row in description_object_ids['records']:
                    if 'EntityDefinitionId' in current_row:
                        entity_definition_id_list.append(current_row['EntityDefinitionId'])
        elif settings.DEBUG:
            print('ERR:description_object_query|' + str(description_object_ids_req.status_code) + '|' + description_object_ids_req.reason)

        for entity_def_id in entity_definition_id_list:
            if utils.is_valid_salesforce_id(entity_def_id):
                # Valid ids need to be looked up.
                target_object_query = f"SELECT Id, FullName FROM CustomField WHERE EntityDefinitionId = '{entity_def_id}'{managed_where_exclude} LIMIT 1"
                target_object_ids_req = requests.get(
                    f"{instance_url}/services/data/v{api_version}/tooling/query/?q=" + urllib.parse.quote(target_object_query, safe=''),
                    headers=headers
                )
                if target_object_ids_req.ok and 'records' in target_object_ids_req.json() and len(target_object_ids_req.json()['records']) > 0:
                    target_record = target_object_ids_req.json()['records'][0]
                    if 'FullName' in target_record:
                        target_object_name = target_record['FullName'].split('.')[0]
                        entity_id_mapping[target_object_name] = entity_def_id
                        entity_id_mapping_rev[entity_def_id] = target_object_name
                        print('mapping object:' + target_object_name + ' => ' + entity_def_id)
                elif settings.DEBUG:
                    print('ERR:target_object_query:' + entity_def_id + '|' + str(target_object_ids_req.status_code) + '|' + target_object_ids_req.reason)


            else:
                # Non-Ids are probably already object names.
                entity_id_mapping[entity_def_id] = entity_def_id
                entity_id_mapping_rev[entity_def_id] = entity_def_id

    try:

        if all_objects.ok and 'sobjects' in all_objects.json():

            for sObject in all_objects.json()['sobjects']:

                object_name = sObject['name']

                if object_name in standard_objects or sObject['name'].endswith('__c'):

                    # Skip managed package objects if we don't want them
                    # Counting to see if "__" appears twice in the object name.
                    if not schema.include_managed_objects and object_name.count('__') > 1:
                        continue

                    # Create object record
                    new_object = Object()
                    new_object.schema = schema
                    new_object.api_name = sObject['name']
                    new_object.label = sObject['label']
                    new_object.save()

                    field_description_map = {}
                    if schema.include_field_description:
                        managed_where_exclude = ''
                        if not schema.include_managed_objects:
                            managed_where_exclude = ' AND NamespacePrefix = NULL'

                        # If the object is not mapped, try mapping it.
                        if new_object.api_name not in entity_id_mapping:
                            if new_object.api_name in standard_objects:
                                entity_id_mapping[new_object.api_name] = new_object.api_name
                            else:
                                object_id_lookup_query = f"SELECT Id, DeveloperName, EntityDefinitionId FROM FieldDefinition WHERE DurableId = '{new_object.api_name}.Id'"
                                object_id_lookup_ids_req = requests.get(
                                    f"{instance_url}/services/data/v{api_version}/query/?q=" + urllib.parse.quote(object_id_lookup_query, safe=''),
                                    headers=headers
                                )
                                if object_id_lookup_ids_req.ok and 'records' in object_id_lookup_ids_req.json() and len(object_id_lookup_ids_req.json()['records']) > 0:
                                    target_lookup_record = object_id_lookup_ids_req.json()['records'][0]
                                    if 'EntityDefinitionId' in target_lookup_record:
                                        entity_id_mapping[new_object.api_name] = target_lookup_record['EntityDefinitionId']
                                        print('second chance mapping object:' + new_object.api_name + ' => ' + target_lookup_record['EntityDefinitionId'])

                        if new_object.api_name in entity_id_mapping:
                            target_object_id = entity_id_mapping[new_object.api_name]
                            object_descriptions_query = f"SELECT Id, Description, DeveloperName, EntityDefinitionId FROM FieldDefinition WHERE EntityDefinitionId = '{target_object_id}' AND Description != NULL"
                            object_descriptions_ids_req = requests.get(
                                f"{instance_url}/services/data/v{api_version}/query/?q=" + urllib.parse.quote(object_descriptions_query, safe=''),
                                headers=headers
                            )
                            if object_descriptions_ids_req.ok and 'records' in object_descriptions_ids_req.json():
                                for current_object_record in object_descriptions_ids_req.json()['records']:
                                    if 'Description' in current_object_record and 'DeveloperName' in current_object_record:
                                        target_field_name = current_object_record['DeveloperName']
                                        field_description_map[target_field_name] = current_object_record['Description']
                                        if settings.DEBUG:
                                            print(f"mapping field (standard): {target_field_name} => {current_object_record['Description']}")
                            elif settings.DEBUG and not object_descriptions_ids_req.ok:
                                print('ERR:object_descriptions_query:' + target_object_id + '|' + str(target_object_ids_req.status_code) + '|' + target_object_ids_req.reason)

                            object_descriptions_custom_query = f"SELECT Id, Description, DeveloperName, EntityDefinitionId, NamespacePrefix FROM CustomField WHERE EntityDefinitionId = '{target_object_id}' AND Description != NULL{managed_where_exclude}"
                            object_descriptions_custom_ids_req = requests.get(
                                f"{instance_url}/services/data/v{api_version}/tooling/query/?q=" + urllib.parse.quote(object_descriptions_custom_query, safe=''),
                                headers=headers
                            )
                            if object_descriptions_custom_ids_req.ok and 'records' in object_descriptions_custom_ids_req.json():
                                for current_object_record in object_descriptions_custom_ids_req.json()['records']:
                                    if 'Description' in current_object_record and 'DeveloperName' in current_object_record:
                                        target_field_name = current_object_record['DeveloperName'] + '__c'
                                        if schema.include_managed_objects and 'NamespacePrefix' in current_object_record and current_object_record['NamespacePrefix'] is not None:
                                            target_field_name = current_object_record['NamespacePrefix'] + '__' + current_object_record['DeveloperName'] + '__c'
                                        field_description_map[target_field_name] = current_object_record['Description']
                                        if settings.DEBUG:
                                            print(f"mapping field (custom): {target_field_name} => {current_object_record['Description']}")
                            elif settings.DEBUG and not object_descriptions_custom_ids_req.ok:
                                print('ERR:object_descriptions_custom_query:' + target_object_id + '|' + str(object_descriptions_custom_ids_req.status_code) + '|' + object_descriptions_custom_ids_req.reason)

                    # query for fields in the object
                    object_describe = requests.get(instance_url + sObject['urls']['describe'], headers={'Authorization': 'Bearer ' + access_token, 'content-type': 'application/json'})

                    if settings.DEBUG and not object_describe.ok:
                        print('ERR:object_describe:' + new_object.label + '|' + str(object_describe.status_code) + '|' + object_describe.reason)

                    # Loop through fields
                    for field in object_describe.json()['fields']:

                        # Get the field name
                        field_name = field['name']

                        # Skip field if it's managed
                        if not schema.include_managed_objects and field_name.count('__') > 1:
                            continue

                        # Create field
                        new_field = Field()
                        new_field.object = new_object
                        new_field.api_name = field_name
                        new_field.label = field['label']

                        if 'inlineHelpText' in field:
                            new_field.help_text = field['inlineHelpText']

                        if schema.include_field_description and new_field.api_name in field_description_map:
                            new_field.description = field_description_map[new_field.api_name]

                        # lookup field
                        if field['type'] == 'reference':
                            new_field.data_type = 'Lookup ('

                            # Could be a list of reference objects
                            for referenceObject in field['referenceTo']:
                                new_field.data_type = new_field.data_type + referenceObject.title() + ', '

                            # remove trailing comma and add closing bracket
                            new_field.data_type = new_field.data_type[:-2]
                            new_field.data_type = new_field.data_type + ')'

                        # Formula field
                        elif field['calculated']:
                            new_field.data_type = 'Formula (' + FIELD_TYPES.get(field['type'], field['type'].title()) + ')'
                            new_field.formula = field.get('calculatedFormula')

                        # picklist values
                        elif field['type'] == 'picklist' or field['type'] == 'multipicklist':
                            new_field.data_type = field['type'].title() + ' ('

                            # Add in picklist values
                            for picklist in field['picklistValues']:
                                if new_field.data_type and picklist.get('label'):
                                    new_field.data_type = new_field.data_type + picklist.get('label',' ') + '; '

                            # remove trailing comma and add closing bracket
                            new_field.data_type = new_field.data_type[:-2]
                            new_field.data_type = new_field.data_type + ')'

                        # Text
                        elif field['type'] == 'string':
                            new_field.data_type = 'Text (' + str(field['length']) + ')'

                        # Int
                        elif field['type'] == 'int':
                            new_field.data_type = 'Number (' + str(field['digits']) + ', 0)'

                        elif field['type'] == 'boolean':
                            new_field.data_type = 'Checkbox'

                        # everything else
                        else:
                            new_field.data_type = field['type'].title()

                            # Change Double to Number
                            if new_field.data_type == 'Double':
                                new_field.data_type = 'Number'

                            # If there is a length component, add to the field type
                            if 'length' in field and int(field['length']) > 0:
                                new_field.data_type += ' (' + str(field['length']) + ')'

                            # If there is a precision element
                            if 'precision' in field and int(field['precision']) > 0:

                                # Determine the number of digits
                                num_digits = int(field['precision']) - int(field['scale'])

                                # Set the precision and scale against the field
                                new_field.data_type += ' (' + str(num_digits) + ', ' + str(field['scale']) + ')'

                        # Add in additional attributes
                        attributes = []

                        if not field.get('nillable'):
                            attributes.append('Required')

                        if field.get('unique'):
                            attributes.append('Unique')

                        if field.get('externalId'):
                            attributes.append('External ID')

                        if field.get('caseSensitive'):
                            attributes.append('Case Sensitive')

                        if attributes:
                            new_field.attributes = ', '.join(attributes)

                        new_field.save()

            
            # If the user wants to see all the places the fields are used
            # run logic to query for other metadata
            if schema.include_field_usage:

                try:

                    # Get all fields for the schema
                    all_fields = Field.objects.filter(object__schema=schema)

                    # Get all layouts usage
                    utils.get_usage_for_component(all_fields, schema, 'Layout')

                    utils.get_usage_for_component(all_fields, schema, 'WorkflowRule')

                    utils.get_usage_for_component(all_fields, schema, 'WorkflowFieldUpdate')

                    utils.get_usage_for_component(all_fields, schema, 'WorkflowOutboundMessage')

                    utils.get_usage_for_component(all_fields, schema, 'EmailTemplate')

                    utils.get_usage_for_component(all_fields, schema, 'Flow')

                    utils.get_usage_for_component(all_fields, schema, 'ApexClass')

                    utils.get_usage_for_component(all_fields, schema, 'ApexComponent')

                    utils.get_usage_for_component(all_fields, schema, 'ApexPage')

                    utils.get_usage_for_component(all_fields, schema, 'ApexTrigger')

                    utils.build_usage_display(all_fields)

                    schema.status = 'Finished'

                except Exception as error:
                    schema.status = 'Error'
                    schema.error = traceback.format_exc()

            else:
                schema.status = 'Finished'

        elif not all_objects.ok:
            schema.status = 'Error'
            schema.error = 'Error running query. The token has probably expired'

            debug = Debug()
            debug.debug = str(all_objects.status_code) + '|' + all_objects.reason + '|' + all_objects.text
            debug.save()

        else:

            schema.status = 'Error'
            schema.error = 'There was no objects returned from the query'

            debug = Debug()
            debug.debug = all_objects.text
            debug.save()

    except Exception as error:
        schema.status = 'Error'
        schema.error = traceback.format_exc()
    
    schema.finished_date = timezone.now()
    schema.save()

    return str(schema.id)


FIELD_TYPES = {
    'boolean': 'Checkbox',
    'int': 'Number',
    'string': 'Text'
}


@shared_task
def job_archival():
    """
    Deletes old jobs to keep the database clean
    """

    one_hour_ago = timezone.now() - datetime.timedelta(minutes=60)
    schemas = Schema.objects.filter(finished_date__lt=one_hour_ago)
    schemas.delete()

    one_day_ago = timezone.now() - datetime.timedelta(hours=24)
    schemas = Schema.objects.filter(created_date__lt=one_day_ago)
    schemas.delete()
