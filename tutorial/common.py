"""
    *************************************************************************************
    *    This file defines some common functions and variables that are used in the
    *    demo and exercise notebooks
    *************************************************************************************
"""

"""
    
"""


"""
    Utilities
"""

import datetime
from datetime import date
from io import BytesIO
import json
import logging
from lxml import etree
import re
import requests
import os
from zipfile import ZipFile
"""
    Globals
"""

 # Poland
set_id = '9200357'

data_dir = f'{os.path.expanduser("~")}/data'
metadata_dir = f'{os.path.expanduser("~")}/temp/metadata/{set_id}'
nsmap = {"cmd": "http://www.clarin.eu/cmd/1",
         "cmdp_text": "http://www.clarin.eu/cmd/1/profiles/clarin.eu:cr1:p_1633000337997"}
output_file = f'{os.path.expanduser("~")}/output'


with open(f'{data_dir}/{set_id}/id_file_map.json', 'r') as id_filename_map_file:
    id_filename_map = json.load(id_filename_map_file)

YYYY_MM_DD = re.compile(r"(?P<year>[0-9]{4})-(?P<month>[0-9]{1,2})-(?P<day>[0-9]{1,2})")
MAX_NER_TASK_SIZE = 30000000

"""
    Metadata printing
"""
def print_xml(tree, declaration: bool = False):
    print(etree.tostring(tree, encoding='UTF-8', xml_declaration=declaration, pretty_print=True).decode())

"""
    Data acess
"""
def get_resource_file(identifier):
    """
        Resolves Europeana subresource identifier to it's local location. 
        
        :param str identifier: Europeana subresource identifier
        :return str: Path to local location of the resource
    """
    if identifier in id_filename_map:
        filename = id_filename_map[identifier]
        return f'{data_dir}/{set_id}/{filename}'

def get_date_from_metadata(metadata_tree):
    dates = metadata_tree.xpath("///cmdp_text:TemporalCoverage/cmdp_text:Start/cmdp_text:date/text()", namespaces=nsmap)
    dates = [YYYY_MM_DD.match(date) for date in dates]
    dates = [datetime.date(int(date.group("year")), int(date.group("month")), int(date.group("day"))) for date in dates]
    return dates
    
def get_description_from_metadata(metadata_tree):
    descriptions = metadata_tree.xpath('//cmdp_text:TextResource/cmdp_text:Description/cmdp_text:description/text()', namespaces=nsmap)
    if len(descriptions) > 0:
        return descriptions[0]
    
def get_resource_ids_from_metadata(metadata_tree):
    ids = metadata_tree.xpath('//cmdp_text:SubresourceDescription/cmdp_text:IdentificationInfo/cmdp_text:identifier/text()', namespaces=nsmap)
    # The result can be any number of identifiers. We do want to filter the values a bit: only the numeric identifiers are useful 
    # to us so we use the special syntax below to make a new list by picking only the matching values from the query results list
    return [id for id in ids if id.isnumeric()]

def get_title_from_metadata(metadata_tree):
    # Get all the values from the xpath
    titles = metadata_tree.xpath('//cmdp_text:TextResource/cmdp_text:TitleInfo/cmdp_text:title/text()', namespaces=nsmap)
    # Check if there is an actual value
    if len(titles) > 0:
        # Return the first (assuming only) value
        return titles[0]

def unpack_metadata(set_id, target_dir):
    # Construct the address of the .zip file with the metadata for one set
    md_zip_url = f'https://europeana-oai.clarin.eu/metadata/fulltext-aggregation/{set_id}.zip'
    
    # Retrieve the .zip file
    print(f'Retrieving {md_zip_url}')
    resp = requests.get(md_zip_url)
    zipfile = ZipFile(BytesIO(resp.content))
    
    # Uncompress the .zip into the target directory
    print(f'Extracting content in {target_dir}')
    zipfile.extractall(path=target_dir)
    print('Done')
    return target_dir

"""
    Zip/Unzip
"""
def zip_file(input_path, output_path=""):
    """
        Zips input file/directory
        
        :param str input_path: path to file to be zipped, if file is directory, entire dir gets zipped
        :param str output_path: path to location, where to save the archive. If empty, zip archive uses same location and name as input
        :returns str: path to archive
    """
    if not output_path:
        output_path = f"{os.path.dirname(input_path)}/{os.path.basename(input_path).split('.')[0]}.zip"
    with ZipFile(output_path, 'r') as zip_handle:
        logger.info(f'Zipping {input_path} to {output_path}')
        if os.path.isdir(input_path):
            _zip_dir(input_path, zip_handle)
        else:
            zip_handle.write(input_path, os.path.basename(input_path))
            # _zip_chunker(input_path)
        
    return output_path
        
def unzip_file(input_path, output_path=""):
    """
        Unzips input .zip file
        
        :param str input_path: path to file to be unzipped
        :param str output_path: path to location, where to unpack the archive. If empty, archive is extracted at its location.
    """
    if not output_path:
        output_path = f"{os.path.dirname(input_path)}/{os.path.basename(input_path).split('.')[0]}"
    with ZipFile(input_path, 'r') as zip_ref:
        logger.info(f'Unzipping {input_path} to {output_path}')
        extracted_files_paths = zip_ref.namelist()
        zip_ref.extractall(output_path)
        
    return [os.path.join(output_path, extracted_file_path) for extracted_file_path in extracted_files_paths]

def _zip_dir(input_dir_path, zip_handle):
    for dirname, subdirs, files in os.walk(input_dir_path):
        for filename in files:          
            logger.info(f'Zipping {dirname}/{filename}')
            # _zip_chunker(os.path.join(dirname, filename))
            zip_handle.write(os.path.join(dirname, filename), 
                             os.path.relpath(os.path.join(dirname, filename), 
                                             os.path.join(input_dir_path, '..')))
             
"""
    Safety
"""
def _check_task_size(resources):
    size = sum([os.path.getsize(resource) for resource in resources])
    if size > MAX_NER_TASK_SIZE:
        raise TaskTooBigError(size, MAX_NER_TASK_SIZE)
        
class TaskTooBigError(Exception):
    """
        Exception raised for tasks with too big payload.
    """

    def __init__(self, size, max_size):
        self.message = f"Tasks payload is too big, it has {size} and maximum is {max_size}"
        super().__init__(self.message)
   
"""
    Logging
"""
logger = logging.getLogger(__name__)

"""
    Exercise cheats
"""

def ex3_filter_by_date_and_content(set_metadata_dir, date_lower, date_upper, target_phrase):
    files = []
    target_phrase_lower = target_phrase.lower()
    for metadata_file in os.listdir(set_metadata_dir):
        full_path = f'{set_metadata_dir}/{metadata_file}'
        tree = etree.parse(full_path)
        for info in _ex3_get_issues_id_and_date(tree):
            (issue_id, issue_date) = info
            if issue_date >= date_lower and issue_date <= date_upper:
                file_path = get_resource_file(issue_id)
                with open(file_path, 'r') as file:
                    while True:
                        line = file.readline()
                        if line:
                            line_lower = line.lower()
                            if target_phrase_lower in line_lower:
                                files.append(file_path)
                                break
                        else:
                            break
    return files

def _ex3_get_issues_id_and_date(metadata_tree):
    """
        Returns a list of tuples (id, date) for all issues in the metadata tree.
        The 'date' part is a date object that supports retrieval of the date parts, i.e.
        `date.year`, `date.month`, `date.day`
    """
    issue_descriptions = metadata_tree.xpath('//cmdp_text:SubresourceDescription', namespaces=nsmap)
    issues = [_ex3_get_id_and_date_from_description(description) for description in issue_descriptions  if description is not None]
    return [issue for issue in issues if issue is not None]

def _ex3_get_id_and_date_from_description(description_element):
    """
        Helper that gets the identifier and date for a single issue. Returns None
        if there is identifier and date information are not both present.
    """
    issue_ids = description_element.findall('./cmdp_text:IdentificationInfo/cmdp_text:identifier', namespaces=nsmap)
    issue_dates_start = description_element.find('./cmdp_text:TemporalCoverage/cmdp_text:Start/cmdp_text:date', namespaces=nsmap)
    if len(issue_ids) > 0 and issue_dates_start is not None:
        for issue_id in issue_ids:
            if issue_id.text.isnumeric():
                return (issue_id.text, date.fromisoformat(issue_dates_start.text))
            
def get_spellchecked_resources_ex3():
    data_root = f"{data_dir}/preprocessed_data/Exercise3/"
    return [f"{data_root}/{filename}" for root, subdir, filenames in os.walk(data_root) for filename in filenames]

def get_spellchecked_resources_ch3():
    data_root = f"{data_dir}/preprocessed_data/Chapter3/"
    
    
    return [f"{os.path.join(root, filename)}" 
            for root, subdir, filenames in os.walk(data_root) 
            for filename in filenames 
            if "speller" in root]

def get_liner_output_files_ch3():
    data_root = f"{data_dir}/preprocessed_data/Chapter3/"
    return [f"{os.path.join(root, filename)}"
            for root, subdir, filenames in os.walk(data_root)
            for filename in filenames
            if "liner.zip" in filename] 

def align_resources(resources_raw, resources_spelled):
    ret = []
    for rraw in resources_raw:
        for rspelled in resources_spelled:
            print(os.path.basename(rraw).split(".")[0])
            print(os.path.basename(rspelled).split(".")[0])
            if os.path.basename(rraw).split(".")[0] == os.path.basename(rspelled).split(".")[0]:
                ret.append((rraw, rspelled))
    return ret
    