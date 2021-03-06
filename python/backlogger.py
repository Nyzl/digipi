# Pulls data from Analytics API and uploads it to BigQuery.

#TODO if no arguments are passed, then request an input from the user

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import pandas_gbq
from pathlib import Path
import os
import sys
import logging


def get_report():

    # Create a custom logger
    logger = logging.getLogger(__name__)

    # Create handlers
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('backlogger.log')
    c_handler.setLevel(logging.WARNING)
    f_handler.setLevel(logging.ERROR)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    try:

        path1 = os.path.dirname(os.path.realpath(__file__))
        parentPath = os.path.dirname(path1)

        SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
        KEY_FILE_LOCATION = os.path.join(parentPath,"creds","backlogger_bq.json")

        VIEW_ID_DICT = {
            'Advisernet':'ga:91978884',
            'All':'ga:77768373',
            'Public':'ga:93356290'
            }

        VIEW_ID = VIEW_ID_DICT[sys.argv[1]]


        rating_body = {
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          'dateRanges': [{'startDate': '90daysAgo', 'endDate': 'yesterday'}],
          'metrics': [{'expression': 'ga:totalEvents'}],
          'dimensions': [
              {'name': 'ga:eventLabel'},
              {'name': 'ga:pagePath'},
              {'name': 'ga:dimension6'}],
          'filtersExpression': ('ga:dimension2!~Start|index;'
            'ga:pagePath!~/about-us/|/local/|/resources-and-tools/|\?;'
            'ga:eventCategory=~pageRating'),
          'orderBys': [{'fieldName': 'ga:totalEvents', 'sortOrder': 'DESCENDING'}],
          'pageSize': 10000
        }]
        }

        size_body = {
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          'dateRanges': [{'startDate': '90daysAgo', 'endDate': 'yesterday'}],
          'metrics': [{'expression': 'ga:pageviews'}],
          'dimensions': [
              {'name': 'ga:pagePath'},
              {'name': 'ga:dimension6'}],
          'filtersExpression': ('ga:dimension2!~Start|index;'
            'ga:pagePath!~/about-us/|/local/|/resources-and-tools/|\?'),
          'orderBys': [{'fieldName': 'ga:pageviews', 'sortOrder': 'DESCENDING'}],
          'pageSize': 10000
        }]
        }

        REPORT_TYPE = {
            'Rating':rating_body,
            'Size':size_body
            }

        report_body = REPORT_TYPE[sys.argv[2]]

        credentials = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE_LOCATION, SCOPES)
        analytics = build('analyticsreporting', 'v4', credentials=credentials)

        response =  analytics.reports().batchGet(
            body= report_body
            ).execute()

        df = pandafy(response)


    ###########$#############################
        # Upload to BigQuery
        cols_dict = {
        'Rating': {'ga:totalEvents':'totalEvents', 'ga:dimension6':'dimension6', 'ga:pagePath':'pagePath', 'ga:eventLabel':'eventLabel'},
        'Size': {'ga:pageviews':'pageviews', 'ga:dimension6':'dimension6', 'ga:pagePath':'pagePath'}
        }

        cols = cols_dict[sys.argv[2]]
        args = sys.argv[1] + sys.argv[2]

        report_name_dict = {
            'AdvisernetRating':'Backlogger.AN_Content_Rating',
            'PublicRating':'Backlogger.Public_Content_Rating',
            'AdvisernetSize':'Backlogger.AN_Content_Size',
            'PublicSize':'Backlogger.Public_Content_Size'
            }

        report_name = report_name_dict[args]

        df2 = df.rename(index=str, columns=cols)
        df2.to_gbq(report_name, 'hardy-album-169409',
                  if_exists = 'replace', private_key=KEY_FILE_LOCATION)


    except ZeroDivisionError:
        logging.error()

    except Exception as ex:
        logging.warning(ex, exc_info=True)
        logging.error("Exception occurred", exc_info=True)

    else:
        return 1




#########################################

def pandafy(response):
  list = []
  # get report data
  for report in response.get('reports', []):
    # set column headers
    columnHeader = report.get('columnHeader', {})
    dimensionHeaders = columnHeader.get('dimensions', [])
    metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])
    rows = report.get('data', {}).get('rows', [])

    for row in rows:
        # create dict for each row
        dict = {}
        dimensions = row.get('dimensions', [])
        dateRangeValues = row.get('metrics', [])

        # fill dict with dimension header (key) and dimension value (value)
        for header, dimension in zip(dimensionHeaders, dimensions):
          dict[header] = dimension

        # fill dict with metric header (key) and metric value (value)
        for i, values in enumerate(dateRangeValues):
          for metric, value in zip(metricHeaders, values.get('values')):
            #set int as int, float a float
            if ',' in value or '.' in value:
              dict[metric.get('name')] = float(value)
            else:
              dict[metric.get('name')] = int(value)

        list.append(dict)

    df = pd.DataFrame(list)
    return df


# Run the functions in order
if __name__ == '__main__':
    VIEW_ID_DICT = {}
    REPORT_TYPE = {}
    get_report()
