import sys
import shutil
import logging

from pathlib import Path
from getpass import getpass
from urllib.parse import urlparse

from utils import cutie
from config_service.config_helper import ConfigHelper
from state_recorder.course import Course
from state_recorder.state_recorder import StateRecorder
from moodle_connector import login_helper
from moodle_connector import sso_token_receiver
from moodle_connector.results_handler import ResultsHandler
from moodle_connector.databases_handler import DatabasesHandler
from moodle_connector.assignments_handler import AssignmentsHandler
from moodle_connector.first_contact_handler import FirstContactHandler
from moodle_connector.request_helper import RequestRejectedError, RequestHelper


class MoodleService:
    def __init__(self, config_helper: ConfigHelper, storage_path: str, skip_cert_verify: bool = False):
        self.config_helper = config_helper
        self.storage_path = storage_path
        self.recorder = StateRecorder(Path(storage_path) / 'moodle_state.db')
        self.skip_cert_verify = skip_cert_verify

    def interactively_acquire_token(self, use_stored_url: bool = False) -> str:
        """
        Walks the user through executing a login into the Moodle-System to get
        the Token and saves it.
        @return: The Token for Moodle.
        """
        print('[The following Credentials are not saved, it is only used temporarily to generate a login token.]')

        moodle_token = None
        while moodle_token is None:

            if not use_stored_url:
                moodle_url = input('URL of Moodle:   ')

                moodle_uri = urlparse(moodle_url)

                moodle_domain, moodle_path = self._split_moodle_uri(moodle_uri)

            else:
                moodle_domain = self.config_helper.get_moodle_domain()
                moodle_path = self.config_helper.get_moodle_path()

            moodle_username = input('Username for Moodle:   ')
            moodle_password = getpass('Password for Moodle [no output]:   ')

            try:
                moodle_token = login_helper.obtain_login_token(
                    moodle_username, moodle_password, moodle_domain, moodle_path, self.skip_cert_verify
                )

            except RequestRejectedError as error:
                print('Login Failed! (%s) Please try again.' % (error))
            except (ValueError, RuntimeError) as error:
                print('Error while communicating with the Moodle System! (%s) Please try again.' % (error))

        # Saves the created token and the successful Moodle parameters.
        self.config_helper.set_property('token', moodle_token)
        self.config_helper.set_property('moodle_domain', moodle_domain)
        self.config_helper.set_property('moodle_path', moodle_path)

        return moodle_token

    def interactively_acquire_sso_token(self, use_stored_url: bool = False) -> str:
        """
        Walks the user through the receiving of a SSO token for the
        Moodle-System and saves it.
        @return: The Token for Moodle.
        """
        if not use_stored_url:

            moodle_url = input('URL of Moodle:   ')

            moodle_uri = urlparse(moodle_url)

            moodle_domain, moodle_path = self._split_moodle_uri(moodle_uri)

        else:
            moodle_domain = self.config_helper.get_moodle_domain()
            moodle_path = self.config_helper.get_moodle_path()

        version = RequestHelper(moodle_domain, moodle_path, '', self.skip_cert_verify).get_simple_moodle_version()

        if version > 3.8:
            print(
                'Between version 3.81 and 3.82 a change was added to'
                + ' Moodle so that automatic copying of the SSO token'
                + ' might not work.'
                + '\nYou can still try it, your version is: '
                + str(version)
            )

        print(' If you want to copy the login-token manual, you will be guided through the manual copy process.')
        do_automatic = cutie.prompt_yes_or_no('Do you want to try to receive the SSO token automatically?')

        print('Please log into Moodle on this computer and then visit the following address in your web browser: ')

        if do_automatic:
            print(
                'https://'
                + moodle_domain
                + moodle_path
                + 'admin/tool/mobile/launch.php?service='
                + 'moodle_mobile_app&passport=12345&'
                + 'urlscheme=http%3A%2F%2Flocalhost'
            )
            moodle_token = sso_token_receiver.receive_token()
        else:
            print(
                'https://'
                + moodle_domain
                + moodle_path
                + 'admin/tool/mobile/launch.php?service='
                + 'moodle_mobile_app&passport=12345'
            )

            print(
                'If you open the link in the browser, no web page should'
                + ' load, instead an error will occur. Open the'
                + ' developer console (press F12) and go to the Network Tab,'
                + ' if there is no error, reload the web page.'
            )

            print(
                'Copy the link address of the website that could not be'
                + ' loaded (right click, then click on Copy, then click'
                + ' on copy link address).'
            )

            print(
                'The script expects a URL that looks something like this:'
                + '`moodlemobile://token=$apptoken`.'
                + ' Where $apptoken looks random. In reality it is a Base64'
                + ' encoded hash and the token we need to access moodle.'
            )

            token_address = input('Then insert the address here:   ')

            moodle_token = sso_token_receiver.extract_token(token_address)
            if moodle_token is None:
                raise ValueError('Invalid URL!')

        # Saves the created token and the successful Moodle parameters.
        self.config_helper.set_property('token', moodle_token)
        self.config_helper.set_property('moodle_domain', moodle_domain)
        self.config_helper.set_property('moodle_path', moodle_path)

        return moodle_token

    def fetch_state(self) -> [Course]:
        """
        Gets the current status of the configured Moodle account and compares
        it with the last known status for changes. It does not change the
        known state, nor does it download the files.
        @return: List with detected changes
        """
        logging.debug('Fetching current Moodle State...')

        token = self.config_helper.get_token()
        moodle_domain = self.config_helper.get_moodle_domain()
        moodle_path = self.config_helper.get_moodle_path()

        request_helper = RequestHelper(moodle_domain, moodle_path, token, self.skip_cert_verify)
        first_contact_handler = FirstContactHandler(request_helper)
        results_handler = ResultsHandler(request_helper)

        download_course_ids = self.config_helper.get_download_course_ids()
        dont_download_course_ids = self.config_helper.get_dont_download_course_ids()
        download_submissions = self.config_helper.get_download_submissions()
        download_descriptions = self.config_helper.get_download_descriptions()
        download_databases = self.config_helper.get_download_databases()

        courses = []
        filtered_courses = []
        try:

            sys.stdout.write('\rDownloading account information')
            sys.stdout.flush()

            userid, version = first_contact_handler.fetch_userid_and_version()
            assignments_handler = AssignmentsHandler(request_helper, version)
            databases_handler = DatabasesHandler(request_helper, version)
            results_handler.setVersion(version)

            courses_list = first_contact_handler.fetch_courses(userid)
            courses = []
            # Filter unselected courses
            for course in courses_list:
                if ResultsHandler._should_download_course(course.id, download_course_ids, dont_download_course_ids):
                    courses.append(course)

            assignments = assignments_handler.fetch_assignments(courses)

            databases = {}
            databases = databases_handler.fetch_databases(courses)
            if download_databases:
                databases = databases_handler.fetch_database_files(databases)

            if download_submissions:
                assignments = assignments_handler.fetch_submissions(userid, assignments)

            index = 0
            for course in courses:
                index += 1

                # to limit the output to one line
                limits = shutil.get_terminal_size()

                shorted_course_name = course.fullname
                if len(course.fullname) > 17:
                    shorted_course_name = course.fullname[:15] + '..'

                into = '\rDownloading course information'

                status_message = into + ' %3d/%3d [%17s|%6s]' % (index, len(courses), shorted_course_name, course.id)

                if len(status_message) > limits.columns:
                    status_message = status_message[0 : limits.columns]

                sys.stdout.write(status_message)
                sys.stdout.flush()

                course_assignments = assignments.get(course.id, {})
                course_databases = databases.get(course.id, {})
                results_handler.set_fetch_addons(course_assignments, course_databases)
                results_handler.set_fetch_options(download_descriptions)
                course.files = results_handler.fetch_files(course.id)

                filtered_courses.append(course)
            print('')

        except (RequestRejectedError, ValueError, RuntimeError) as error:
            raise RuntimeError('Error while communicating with the Moodle System! (%s)' % (error))

        logging.debug('Checking for changes...')
        changes = self.recorder.changes_of_new_version(filtered_courses)

        # Filter changes
        changes = self._filter_courses(
            changes,
            download_course_ids,
            dont_download_course_ids,
            download_submissions,
            download_descriptions,
            download_databases,
        )

        changes = self.add_options_to_courses(changes)

        return changes

    def add_options_to_courses(self, courses: [Course]):
        """
        Updates a array of courses with its options
        """
        options_of_courses = self.config_helper.get_options_of_courses()
        for course in courses:
            options = options_of_courses.get(str(course.id), None)
            if options is not None:
                course.overwrite_name_with = options.get('overwrite_name_with', None)
                course.create_directory_structure = options.get('create_directory_structure', True)

        return courses

    @staticmethod
    def _filter_courses(
        changes: [Course],
        download_course_ids: [int],
        dont_download_course_ids: [int],
        download_submissions: bool,
        download_descriptions: bool,
        download_databases: bool,
    ) -> [Course]:
        """
        Filters the changes course list from courses that
        should not get downloaded
        @param download_course_ids: list of course ids
                                         that should be downloaded
        @param dont_download_course_ids: list of course ids
                                         that should not be downloaded
        @param download_submissions: boolean if submissions
                                    should be downloaded
        @param download_descriptions: boolean if descriptions
                                    should be downloaded
        @param download_databases: boolean if databases should be downloaded
        @return: filtered changes course list
        """

        filtered_changes = []

        for course in changes:
            if not download_submissions:
                course_files = []
                for file in course.files:
                    if file.content_type != 'submission_file':
                        course_files.append(file)
                course.files = course_files

            if not download_descriptions:
                course_files = []
                for file in course.files:
                    if file.content_type != 'description':
                        course_files.append(file)
                course.files = course_files

            if not download_databases:
                course_files = []
                for file in course.files:
                    if file.content_type != 'database_file':
                        course_files.append(file)
                course.files = course_files

            if (
                ResultsHandler._should_download_course(course.id, download_course_ids, dont_download_course_ids)
                and len(course.files) > 0
            ):
                filtered_changes.append(course)

        return filtered_changes

    @staticmethod
    def _split_moodle_uri(moodle_uri: str):
        """
        Splits a given Moodle-Uri into the domain and the installation path
        @return: moodle_domain, moodle_path as strings
        """

        moodle_domain = moodle_uri.netloc
        moodle_path = moodle_uri.path
        if not moodle_path.endswith('/'):
            moodle_path = moodle_path + '/'

        if moodle_path == '':
            moodle_path = '/'

        return moodle_domain, moodle_path
