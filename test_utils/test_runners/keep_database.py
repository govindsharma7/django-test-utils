from django.test.simple import *
import os

def run_tests(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    """
    worsk exactly as per normal test
    but only creates the test_db if it doesn't yet exist
    and does not destroy it when done
    tables are flushed and fixtures loaded between tests as per usual
    but if your schema has not changed then this saves significant amounts of time
    and speeds up the test cycle

    Run the unit tests for all the test labels in the provided list.
    Labels must be of the form:
     - app.TestClass.test_method
        Run a single specific test method
     - app.TestClass
        Run all the test methods in a given class
     - app
        Search for doctests and unittests in the named application.

    When looking for tests, the test runner will look in the models and
    tests modules for the application.

    A list of 'extra' tests may also be provided; these tests
    will be added to the test suite.

    Returns the number of tests that failed.
    """
    setup_test_environment()

    settings.DEBUG = False
    suite = unittest.TestSuite()

    if test_labels:
        for label in test_labels:
            if '.' in label:
                suite.addTest(build_test(label))
            else:
                app = get_app(label)
                suite.addTest(build_suite(app))
    else:
        for app in get_apps():
            suite.addTest(build_suite(app))

    for test in extra_tests:
        suite.addTest(test)

    suite = reorder_suite(suite, (TestCase,))

    ###Everything up to here is from django.test.simple

    from django.db.backends import creation
    from django.db import connections, DatabaseError

    old_name = {}
    for alias in connections:
        connection = connections[alias]
        old_name[alias] = settings.DATABASES[alias]['NAME']

        if settings.DATABASES[alias]['TEST_NAME']:
            settings.DATABASES[alias]['NAME'] = settings.DATABASES[alias]['TEST_NAME']
        else:
            settings.DATABASES[alias]['NAME'] = creation.TEST_DATABASE_PREFIX + settings.DATABASES[alias]['NAME']
        connection.settings_dict["DATABASE_NAME"] = settings.DATABASES[alias]['NAME']

        # does test db exist already ?
        try:
            if settings.DATABASES[alias]['ENGINE'] == 'sqlite3':
                if not os.path.exists(settings.DATABASES[alias]['NAME']):
                    raise DatabaseError
            connection.cursor()
        except Exception:
            print 'database %s does not exist. creating...' % alias
            # db does not exist
            # juggling !  create_test_db switches the DATABASE_NAME to the TEST_DATABASE_NAME
            settings.DATABASES[alias]['NAME'] = old_name[alias]
            connection.settings_dict["DATABASE_NAME"] = old_name[alias]
            connection.creation.create_test_db(verbosity, autoclobber=True)
        else:
            connection.close()

        settings.DATABASES[alias]['SUPPORTS_TRANSACTIONS'] = connection.creation._rollback_works()

    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)

    for alias in settings.DATABASES:
        #Since we don't call destory_test_db, we need to set the db name back.
        settings.DATABASES[alias]['NAME'] = old_name[alias]
        connection.settings_dict["DATABASE_NAME"] = old_name[alias]

    teardown_test_environment()

    return len(result.failures) + len(result.errors)
