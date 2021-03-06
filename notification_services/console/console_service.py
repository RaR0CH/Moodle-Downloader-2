import logging

from utils.logger import Log
from state_recorder.course import Course
from notification_services.notification_service import NotificationService


class ConsoleService(NotificationService):
    def interactively_configure(self) -> None:
        raise RuntimeError('Not yet implemendet!')

    def notify_about_changes_in_moodle(self, changes: [Course]) -> None:
        """
        Creates a terminal output about the downloaded changes.
        @param changes: A list of changed courses with changed files.
        """
        RESET_SEQ = '\033[0m'
        COLOR_SEQ = '\033[1;%dm'

        BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)
        print('\n')

        diff_count = 0
        for course in changes:
            diff_count += len(course.files)

        if diff_count > 0:
            logging.info('%s changes found for the configured Moodle-Account.' % (diff_count))

            Log.success('%s changes found for the configured Moodle-Account.' % (diff_count))

        for course in changes:
            if len(course.files) == 0:
                continue

            print(COLOR_SEQ % BLUE + course.fullname + RESET_SEQ)

            for file in course.files:
                if file.modified:
                    print(COLOR_SEQ % YELLOW + '≠\t' + file.saved_to + RESET_SEQ)

                elif file.moved:
                    if file.new_file is not None:
                        print(
                            COLOR_SEQ % CYAN
                            + '<->\t'
                            + (
                                file.saved_to
                                + RESET_SEQ
                                + COLOR_SEQ % GREEN
                                + ' ==> '
                                + file.new_file.saved_to
                                + RESET_SEQ
                            )
                        )
                    else:
                        print(COLOR_SEQ % CYAN + '<->\t' + file.saved_to + RESET_SEQ)

                elif file.deleted:
                    print(COLOR_SEQ % MAGENTA + '-\t' + file.saved_to + RESET_SEQ)

                else:
                    print(COLOR_SEQ % GREEN + '+\t' + file.saved_to + RESET_SEQ)
            print('\n')

    def notify_about_error(self, error_description: str):
        raise RuntimeError('Not yet implemented!')
