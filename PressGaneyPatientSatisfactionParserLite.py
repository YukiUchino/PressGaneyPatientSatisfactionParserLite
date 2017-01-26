import os
import csv
import configparser
import xmltodict
import pysftp


# Configurations
config = configparser.ConfigParser()
config.read('configuration.ini')
_client_id = config['DEFAULT']['ClientId']
_patient_id_type = config['DEFAULT']['EhrPatientIdType']
_encounter_id_type = config['DEFAULT']['EhrEncounterIdType']
_press_ganey_record_id_type = config['DEFAULT']['PressGaneyRecordIdType']
_press_ganey_key = config['DEFAULT']['PressGaneyKey']
_press_ganey_secret = config['DEFAULT']['PressGaneySecret']

# Dictionary data structs for holding the objects parsed during the execution.
surveys = {}
answers = {}
questions = {}

# Classes for representing Surveys, SurveyQuestions, SurveyAnswers
class Survey(object):
    def __init__(self ,id=None ,idtype=None ,name=None
                ,type=None ,description=None ,**kwargs):
        self.Id = id
        self.IdType = idtype
        self.Name = name
        self.Type = type
        self.Description = description
        self.ClientId =_client_id
        return super().__init__(**kwargs)
class SurveyQuestion(object):
    def __init__(self ,id=None ,idtype=None ,name=None ,text=None
                ,responsetype=None ,acceptableresponse=None ,surveyid=None
                ,surveyidtype=None ,**kwargs):
        self.Id = id
        self.IdType = idtype
        self.SurveyId = surveyid
        self.SurveyIdType = surveyidtype
        self.Name = name
        self.Text = text
        self.ResponseType = responsetype
        self.AcceptableResponse = acceptableresponse
        self.ClientId =_client_id
        return super().__init__(**kwargs)
class SurveyAnswer(object):
    def __init__(self ,id=None ,idtype=None ,patientid=None ,patientidtype=None
                ,providerid=None ,provideridtype=None ,locationid=None
                ,locationidtype=None ,encounterid=None ,encounteridtype=None
                ,accountid=None ,accountidtype=None ,surveyid=None
                ,surveyidtype=None ,surveyquestionid=None ,surveyquestionidtype=None
                ,responsedate=None ,encounterdate=None ,response=None
                ,responsenumeric=None ,**kwargs):
        self.Id=id
        self.IdType=idtype
        self.PatientId=patientid
        self.PatientIdType=patientidtype
        self.ProviderId=providerid
        self.ProviderIdType=provideridtype
        self.LocationId=locationid
        self.LocationIdType=locationidtype
        self.EncounterId=encounterid
        self.EncounterIdType=encounteridtype
        self.AccountId=accountid
        self.AccountIdType=accountidtype
        self.SurveyId=surveyid
        self.SurveyIdType=surveyidtype
        self.SurveyQuestionId=surveyquestionid
        self.SurveyQuestionIdType=surveyquestionidtype
        self.ResponseDate=responsedate
        self.EncounterDate=encounterdate
        self.Response=response
        self.ResponseNumeric=responsenumeric
        self.ClientId =_client_id
        return super().__init__(**kwargs)

# Create data directories if they don't exist
rawdata_directory = os.path.join(os.getcwd(),'rawdata')
if not os.path.isdir(rawdata_directory):
    os.mkdir(rawdata_directory)
data_directory = os.path.join(os.getcwd(),'data')
if not os.path.isdir(data_directory):
    os.mkdir(data_directory)

# Disable host key checking
cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

# Only SFTP fetch files we don't have, deposit them into the rawdata directory
with pysftp.Connection('ftp.pressganey.com', username=_press_ganey_key, password=_press_ganey_secret, cnopts=cnopts) as sftp:
    already_fetched_filenames = [f for f in os.listdir(rawdata_directory)]
    remote_files = [f for f in sftp.listdir('')]
    files_to_fetch = [f for f in remote_files if f not in already_fetched_filenames and '.xml' in f]
    for filename in files_to_fetch:
        sftp.get(filename, os.path.join(rawdata_directory, filename), preserve_mtime=True)

# Parse Press Ganey XML into python objects and add to appropriate dictionary data struct
for f in os.listdir(rawdata_directory):
    with open(os.path.join(rawdata_directory, f)) as fd:
        doc = xmltodict.parse(fd.read())

        # Parse Questions
        for question in doc['DATA_EXPORT']['HEADER']['QUESTION_MAP']['QUESTION']:
            question_id = "{0}|{1}".format(question['SERVICE'], question['VARNAME'])
            if question_id not in surveys.keys():
                questions[question_id] =  SurveyQuestion(id=question_id
                                                        ,idtype=_press_ganey_record_id_type
                                                        ,surveyid=question['SERVICE']
                                                        ,surveyidtype=_press_ganey_record_id_type
                                                        ,name=question['VARNAME']
                                                        ,text=question['QUESTION_TEXT']
                                                        ,responsetype=None
                                                        ,acceptableresponse=None)
                
        # Parse Answers
        for srv in doc['DATA_EXPORT']['PATIENTLEVELDATA']:

            # Parse Survey Metadata
            survey_date = doc['DATA_EXPORT']['HEADER']['RECDATE']['START']
            pat_id = ""
            encounter_id = ""
            admit_date = ""
            for ans in [a for a in srv['DEMOGRAPHICS']['RESPONSE'] if a['VARNAME'] in ("ITMEDREC","ITUNIQUE","ITADMDAT")]:
                if ans['VARNAME'] == 'ITMEDREC':
                    pat_id = ans['VALUE']
                if ans['VARNAME'] == 'ITUNIQUE':
                    encounter_id = ans['VALUE']
                if ans['VARNAME'] == 'ITADMDAT':
                    admit_date = ans['VALUE']

            # Parse answers from demographics section
            if srv['DEMOGRAPHICS'] is not None:
                for ans in srv['DEMOGRAPHICS']['RESPONSE']:
                    answer = SurveyAnswer()
                    answer.Id = "{0}|{1}|{2}|{3}".format(_client_id
                                    ,srv['SURVEY_ID']
                                    ,srv['SERVICE']
                                    ,ans['VARNAME'])
                    answer.IdType = _press_ganey_record_id_type
                    answer.PatientId = pat_id
                    answer.PatientIdType = _patient_id_type
                    answer.EncounterId = encounter_id
                    answer.EncounterIdType = _encounter_id_type
                    answer.SurveyId = srv['SERVICE']
                    answer.SurveyIdType = _press_ganey_record_id_type
                    answer.SurveyQuestionId = "{0}|{1}".format(srv['SERVICE'], ans['VARNAME'])
                    answer.SurveyQuestionIdType = _press_ganey_record_id_type
                    answer.ResponseDate = srv['RECDATE']
                    answer.Response = ans['VALUE']
                    answers[answer.Id] = answer

            # Parse answers from "ANALYSIS" section
            if srv['ANALYSIS'] is not None:
                for ans in srv['ANALYSIS']['RESPONSE']:
                    answer = SurveyAnswer()
                    if type(ans) == type(""):
                        answer.Id = "{0}|{1}|{2}|{3}".format(_client_id
                                        ,srv['SURVEY_ID'] or ""
                                        ,srv['SERVICE'] or ""
                                        ,ans or "")
                        answer.IdType = _press_ganey_record_id_type
                        answer.PatientId = pat_id
                        answer.PatientIdType = _patient_id_type
                        answer.EncounterId = encounter_id
                        answer.EncounterIdType = _encounter_id_type
                        answer.SurveyId = srv['SERVICE']
                        answer.SurveyIdType = _press_ganey_record_id_type
                        answer.SurveyQuestionId = "{0}|{1}".format(question['SERVICE'], ans)
                        answer.SurveyQuestionIdType = _press_ganey_record_id_type
                        answer.ResponseDate = srv['RECDATE'] or None
                        answer.Response = ans
                        answers[answer.Id] = answer
                    else:
                        answer.Id = "{0}|{1}|{2}|{3}".format(_client_id
                                        ,srv['SURVEY_ID']
                                        ,srv['SERVICE']
                                        ,ans['VARNAME'])
                        answer.IdType = _press_ganey_record_id_type
                        answer.PatientId = pat_id
                        answer.PatientIdType = _patient_id_type
                        answer.EncounterId = encounter_id
                        answer.EncounterIdType = _encounter_id_type
                        answer.SurveyId = srv['SERVICE']
                        answer.SurveyIdType = _press_ganey_record_id_type
                        answer.SurveyQuestionId = "{0}|{1}".format(question['SERVICE'], ans['VARNAME'])
                        answer.SurveyQuestionIdType = _press_ganey_record_id_type
                        answer.ResponseDate = srv['RECDATE'] or None
                        answer.ResponseNumeric = int(ans['VALUE']) or None
                        answer.Response = ans['VALUE']
                        answers[answer.Id] = answer

            # Parse answers from "HCAHPS" section
            if srv['HCAHPS'] is not None:
                for ans in srv['HCAHPS']['RESPONSE']:
                    answer = SurveyAnswer()
                    answer.Id = "{0}|{1}|{2}|{3}".format(_client_id
                                    ,srv['SURVEY_ID']
                                    ,srv['SERVICE']
                                    ,ans['VARNAME'])
                    answer.IdType = "ExternalPressGaneyId"
                    answer.PatientId = pat_id
                    answer.PatientIdType = _patient_id_type
                    answer.EncounterId = encounter_id
                    answer.EncounterIdType = _encounter_id_type
                    answer.SurveyId = srv['SERVICE']
                    answer.SurveyIdType = _press_ganey_record_id_type
                    answer.SurveyQuestionId = "{0}|{1}".format(srv['SERVICE'], ans['VARNAME'])
                    answer.SurveyQuestionIdType = _press_ganey_record_id_type
                    answer.ResponseDate = srv['RECDATE']
                    answer.Response = ans['VALUE']
                    answers[answer.Id] = answer

# Write surveys to csv
with open(os.path.join(data_directory,'surveys.csv'), 'w') as output:
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    writer.writerow(['Id','IdType', 'Name'])
    for sid in list(set([questions[s].SurveyId for s in questions.keys()])):
        writer.writerow([sid,_press_ganey_record_id_type, sid])

# Write questions to csv
with open(os.path.join(data_directory,'questions.csv'), 'w') as output:
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    writer.writerow(['Id','IdType','SurveyId','SurveyIdType','Name','Text','ResponseType','AcceptableResponse','ClientId'])
    for q in questions.values():
        writer.writerow([str(q.Id) or "" ,str(q.IdType) or "" ,str(q.SurveyId) or ""
                        ,str(q.SurveyIdType) or "" ,str(q.Name) or "" ,str(q.Text) or ""
                        ,str(q.ResponseType) or "" ,str(q.AcceptableResponse) or "" ,str(q.ClientId) or ""
        ])

# Write answers to csv
with open(os.path.join(data_directory,'answers.csv'), 'w') as output:
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    writer.writerow(['Id' ,'IdType' ,'PatientId' ,'PatientIdType' ,'ProviderId'
                    ,'ProviderIdType' ,'LocationId' ,'LocationIdType' ,'EncounterId'
                    ,'EncounterIdType' ,'AccountId' ,'AccountIdType' ,'SurveyId'
                    ,'SurveyIdType' ,'SurveyQuestionId' ,'SurveyQuestionIdType' ,'ResponseDate'
                    ,'EncounterDate' ,'Response' ,'ResponseNumeric' ,'ClientId'
    ])
    for a in answers.values():
        writer.writerow([a.Id ,a.IdType ,a.PatientId ,a.PatientIdType
                        ,a.ProviderId ,a.ProviderIdType ,a.LocationId
                        ,a.LocationIdType ,a.EncounterId ,a.EncounterIdType
                        ,a.AccountId ,a.AccountIdType ,a.SurveyId ,a.SurveyIdType
                        ,a.SurveyQuestionId ,a.SurveyQuestionIdType ,a.ResponseDate
                        ,a.EncounterDate ,a.Response ,a.ResponseNumeric ,a.ClientId
        ])

# Write single-file complete data export to csv
with open(os.path.join(data_directory,'alldata.csv'), 'w') as output:
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    writer.writerow(['ClientId','AnswerId','AnswerIdType'
                    ,'PatientId','PatientIdType'
                    ,'ProviderId','ProviderIdType'
                    ,'SurveyId','SurveyIdType'
                    ,'QuestionId','QuestionIdType','QuestionName','QuestionText','ResponseType','AcceptableResponse'
                    ,'LocationId','LocationIdType'
                    ,'EncounterId','EncounterIdType','EncounterDate'
                    ,'AccountId','AccountIdType'
                    ,'ResponseDate' ,'Response','ResponseNumeric'
    ])
    for a in answers.values():
        # Get Question Data
        if a.SurveyQuestionId in questions.keys():
            question_name = questions[a.SurveyQuestionId].Name
            question_text = questions[a.SurveyQuestionId].Text
            question_responsetype = questions[a.SurveyQuestionId].ResponseType
            question_acceptableresponse = questions[a.SurveyQuestionId].AcceptableResponse
        else:
            question_name = ""
            question_text = ""
            question_responsetype = ""
            question_acceptableresponse = ""
        writer.writerow([a.ClientId ,a.Id ,a.IdType
                        ,a.PatientId ,a.PatientIdType
                        ,a.ProviderId ,a.ProviderIdType
                        ,a.SurveyId ,a.SurveyIdType
                        ,a.SurveyQuestionId ,a.SurveyQuestionIdType ,question_name ,question_text ,question_responsetype ,question_acceptableresponse
                        ,a.LocationId ,a.LocationIdType
                        ,a.EncounterId ,a.EncounterIdType ,a.EncounterDate
                        ,a.AccountId ,a.AccountIdType
                        ,a.ResponseDate ,a.Response ,a.ResponseNumeric
        ])
