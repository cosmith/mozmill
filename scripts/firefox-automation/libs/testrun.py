# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is MozMill automation code.
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Henrik Skupin <hskupin@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

mozmill_tests_repository = "http://hg.mozilla.org/qa/mozmill-tests"

# global modules
import os, sys
import tempfile

# local modules
import application
import install
import mozmill_wrapper
import repository

class TestRun(object):
    """ Class to execute a Mozmill test-run. """

    def __init__(self, *args, **kwargs):
        self.binaries = [ ]
        self.repository_path = ""
        self.repository_url = mozmill_tests_repository
        self.test_path = ""

    def _get_binaries(self):
        """ Returns the list of binaries to test. """
        return self._binaries

    def _set_binaries(self, value):
        """ Sets the list of binaries to test. """
        self._binaries = [ ]

        if value is None:
            return

        for path in value:
            if not os.path.exists(path):
                raise Exception("Path '%s' cannot be found." % (path))

            # Check if it's an installer or an already installed build
            if self.is_installer(path) or application.is_app_folder(path):
                self._binaries.append(os.path.abspath(path))
                continue
            # Otherwise recursivily scan the folder and add existing files
            for root, dirs, files in os.walk(path):
                for file in files:
                    if not file in [".DS_Store"] and self.is_installer(file):
                        self._binaries.append(os.path.abspath(os.path.join(root, file)))

    binaries = property(_get_binaries, _set_binaries, None)

    def _get_report_url(self):
        """ Returns the URL of the report server. """
        return self._report_url

    def _set_report_url(self, value):
        """ Sets the URL of the report server. """
        self._report_url = value

    report_url = property(_get_report_url, _set_report_url)

    def _get_repository_path(self):
        """ Returns the local location of the repository. """
        return self._repository_path

    def _set_repository_path(self, value):
        """ Sets the local location of the repository. """
        self._repository_path = value

    repository_path = property(_get_repository_path, _set_repository_path)

    def _get_repository_url(self):
        """ Returns the remote location of the repository. """
        return self._repository_url

    def _set_repository_url(self, value):
        """ Sets the remote location of the repository. """
        self._repository_url = value

    repository_url = property(_get_repository_url, _set_repository_url)

    def _get_test_path(self):
        """ Returns the relative test path inside the repository. """
        return self._test_path

    def _set_test_path(self, value):
        """ Sets the relative test path inside the repository. """
        self._test_path = value

    test_path = property(_get_test_path, _set_test_path)

    def cleanup_binary(self, binary, *args, **kwargs):
        """ Remove the build when it has been installed before. """
        if self.is_installer(binary):
            install.Installer().uninstall(self._folder)

    def cleanup_repository(self, *args, **kwargs):
        """ Removes the local version of the repository. """
        self._repository.remove()

    def clone_repository(self, *args, **kwargs):
        """ Clones the repository to a local temporary location. """
        try:
            self.repository_path = tempfile.mkdtemp(".mozmill-tests")
            self._repository = repository.Repository(self.repository_url,
                                                     self.repository_path)
            self._repository.clone()
        except Exception, e:
            raise Exception("Failure in setting up the mozmill-tests repository. " +
                            e.message)

    def is_installer(self, path):
        """ Checks if a binary is an installer. """
        try:
            return os.path.splitext(path)[1] in (".bz2", ".dmg", ".exe", ".zip")
        except:
            return False

    def prepare_binary(self, binary, *args, **kwargs):
        """ Prepare the binary for the test run. """

        if self.is_installer(binary):
            install_path = tempfile.mkdtemp(".binary")
            self._folder = install.Installer().install(binary, install_path)
            self._application = application.get_binary(self._folder)
        else:
            folder = os.path.dirname(binary)
            self._folder = folder if not os.path.isdir(binary) else binary
            self._application = binary

    def prepare_repository(self, *args, **kwargs):
        """ Update the repository to the needed branch. """

        # Retrieve the Gecko branch from the application.ini file
        ini = application.ApplicationIni(self._folder)
        repository_url = ini.get('App', 'SourceRepository')

        # Update the mozmill-test repository to match the Gecko branch
        branch_name = self._repository.identify_branch(repository_url)
        self._repository.update(branch_name)

    def _init_test_data(self, *args, **kwargs):
        """ Initialize the test-run data. """
        self._mozmill.binary = self._application
        self._mozmill.report = self.report_url
        self._mozmill.test = os.path.join(self.repository_path, self.test_path)

    def run_test(self, *args, **kwargs):
        self._mozmill = mozmill_wrapper.MozmillWrapperCLI()
        self._init_test_data()
        self._mozmill.run()

    ''' Run software update tests for all specified builds '''
    def run(self, *args, **kwargs):
        self.clone_repository()

        # Run tests for each binary
        for binary in self.binaries:
            try:
                self.prepare_binary(binary)
                self.prepare_repository()
                self.run_test()
            except Exception, e:
                print e.message

            self.cleanup_binary(binary)

        self.cleanup_repository()


class RestartTestRun(TestRun):

    def run_test(self, *args, **kwargs):
        try:
            self._mozmill = mozmill_wrapper.MozmillWrapperRestartCLI()
            self._init_test_data()
            self._mozmill.run()
        except Exception, e:
            print e.message
