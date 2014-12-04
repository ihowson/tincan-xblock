"""
XBlock to display SCORM content.
Right now, this is targeting the SCORM 2014 API.

FIXME: No consideration has been given to security. Don't let untrusted staff use this.

I'm targeting Articulate Storyline first per the document at https://en-uk.articulate.com/tincanapi/
"""

# The path that SCORM content is stored in
# FIXME: nasty
DEFAULT_SCORM_PATH = '/edx/app/edxapp/edx-platform/scorm'

import json
from lxml import etree
import os
import os.path
import pkg_resources
from threading import Lock
import urllib
from webob import Response
import webob.exc

from xblock.core import XBlock
from xblock.fields import Scope, String, Dict  # , Field, BlockScope
from xblock.fragment import Fragment
#from xblock.runtime import KeyValueStore


class SCORMXBlock(XBlock):
    """
    XBlock wrapper for SCORM content objects
    """

    scorm_dir = String(help="Directory that the SCORM content object is stored in", default=None, scope=Scope.settings)

    # FIXME: dodgy hack to ease debugging under Workbench
    override_scorm_path = String(default=None, scope=Scope.settings)

    lock = Lock()
    scorm_data = Dict(
        scope=Scope.user_state,
        help="Temporary storage for SCORM data",
    )

    # Tin Can data model
    tc_activities_state = Dict(default={}, scope=Scope.user_state)  # stateId -> JSON document
    tc_statements = Dict(default={}, scope=Scope.user_state)  # statementId -> JSON document




    cmi_completion_status = String(default='unknown', scope=Scope.user_state)
    # cmi_entry = String(default=TODO, scope=Scope.user_state)

    def __init__(self, *args, **kwargs):
        XBlock.__init__(self, *args, **kwargs)

        self.scorm_path = DEFAULT_SCORM_PATH
        if self.override_scorm_path:
            self.scorm_path = self.override_scorm_path

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def studio_view(self, context=None):
        try:
            try:
                ls = os.listdir(self.scorm_path)
            except OSError, e:
                return Fragment(u"ERROR: couldn't read SCORM directory (%s). The full error is '%s'." % (self.scorm_path, e))

            # make a list of available SCORMs
            scorms = []
            for dirname in ls:
                # check if there is a manifest
                if os.path.isfile(os.path.join(self.scorm_path, dirname, 'tincan.xml')):
                    scorms.append(dirname)

            frag = Fragment(content=u'<h2>Available SCORMs</h2><ul>')
            # TODO push all of this to a Mako/jinja template somewhere

            if scorms:
                for s in scorms:
                    url = 'TODO'
                    checked = ''
                    if self.scorm_dir == dirname:
                        checked = ' checked'

                    frag.add_content(u"<input type='radio' name='scorm_dir' value='%s'%s> %s (<a href='%s'>preview</a>)<br />" % (s, checked, s, url))
                frag.add_content(u"<a href='#' class='button action-primary save-button'>Save</a>")
            else:
                frag.add_content(u"There isn't any SCORM content available. Please check that you've unzipped your content into the '%s' directory and try again." % self.scorm_path)

            frag.add_javascript(self.resource_string("static/studio.js"))
            frag.initialize_js('SCORMStudioXBlock')
        except Exception, e:
            # This is horrible and nasty, but this way we actually get some debug info.
            import traceback
            print traceback.print_exc()
            frag = Fragment(unicode(e))

        return frag

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        self.scorm_dir = data.get('scorm_dir')

        return {'result': 'success'}

    @XBlock.handler
    def tincan_req(self, data, suffix=''):
        '''
        JSON endpoint for Tin Can client requests.

        All methods are multiplexed through this function.

        This is an unauthenticated handler, so we must check CSRF and user auth
        manually.
        '''

        if data.method != 'POST':
            assert False, 'unknown method %s' % data.method

        # TODO look at rebind_noauth_module_to_user when we know the intended user
        # print 'scope_ids: ', self.scope_ids
        # print user

        method = None

        # TODO FIXME IMPORTANT: check csrf token explicitly here
        print 'FIXME: no CSRF check on tincan_req yet'

        # Workbench gives us annoying 'student=student_1activities/state?method=GET' things. Fix it up.
        if 'student' in data.params.keys() and suffix == '':
            # strip student_1 off the front
            # this is the lazy way; we could do an RE, but then I would have two problems
            val = data.params['student']
            if val.startswith('student_1'):
                val = val[9:]

            (suffix, method_pair) = val.split('?')

            (method_title, method) = method_pair.split('=')
            assert method_title == 'method'

        if 'method' in data.params:
            method = data.params['method']

        assert method is not None, 'no method'

        try:
            response = self.tincan_handle(method, suffix, data.POST)
        except webob.exc.HTTPException, e:
            return e

        return Response(json.dumps(response), content_type='application/json')

    @staticmethod
    def requireParams(dictionary, expected_keys):
        '''
        expected_keys is a list of key names that should be present in
        'dictionary'. If any are missing, raise a 400 Bad Request.
        '''

        for k in expected_keys:
            if k not in dictionary.keys():
                raise webob.exc.HTTPBadRequest('expected key "%s", not found' % k)

    def tincan_handle(self, method, suffix, post):
        '''
        Returns a JSON string for a successful 200 request. Raises a
        webob.exc.HTTPException in case of error (or non-200 response).

        post: the HTTP POST parameters
        '''

        # demux
        print 'method %s %s' % (method, suffix)
        if suffix == 'activities/state':
            if method == 'GET':
                if 'stateId' in post.keys():
                    # return a single document
                    sid = post['stateId']
                    if sid in self.tc_activities_state.keys():
                        return self.tc_activities_state[sid]
                    else:
                        return ''
                else:
                    # this should return the available ids
                    pass  # not implemented
            elif method == 'PUT':
                self.requireParams(post, ['stateId', 'content'])
                # TODO handle context parameters
                self.tc_activities_state[post['stateId']] = post['content']
                # self.save()

                raise webob.exc.HTTPNoContent
        elif suffix == 'statements':
            if method == 'PUT':
                self.requireParams(post, ['statementId', 'content'])

                sid = post['statementId']
                content = post['content']

                # does it already exist?
                if sid in self.tc_statements.keys():
                    # If it's different, return 409 Conflict. If same, return 204 No Content.
                    # TODO: would be better to check logical JSON equality rather than byte equality
                    if self.tc_statements[sid] == content:
                        raise webob.exc.HTTPNoContent()
                    else:
                        raise webob.exc.HTTPConflict()
                else:
                    # store it
                    self.tc_statements[sid] = content

                    # TODO: eventually, we can process these asynchronously
                    # using celery so we don't block the web server. For now,
                    # this is easier (but slower).
                    self.tc_statement_process(content)

                    raise webob.exc.HTTPNoContent()

        '''
        elif suffix == 'activities/profile' and method == 'POST':
            pass
        elif suffix == 'agent/profile' and method == 'POST':
            pass
            '''

        print 'tincan_handle: unhandled method %s %s' % (method, suffix)
        return webob.exc.HTTPNotImplemented()  # FIXME: change this to 'unknown method' when appropriate (when you've implemented a good number of endpoints)

    @XBlock.json_handler
    def sco_req(self, data, suffix=''):
        """
        JSON request from the student's SCO.

        This is multiplexed to handle all of the GetValue/SetValue/etc requests
        through one entry point.
        """

        assert 'method' in data.keys(), 'not implemented'  # should return a 'bad request' to SCO

        method = data['method']

        if method == 'getValue':
            assert 'name' in data.keys(), 'TODO return "bad request"'
            result = self.model.get(data['name'])
        elif method == 'setValue':
            assert 'name' in data.keys(), 'TODO return "bad request"'
            assert 'value' in data.keys(), 'TODO return "bad request"'
            result = self.model.set(data['name'])
        else:
            print 'not implemented method %s' % method
            assert False, 'not implemented'  # should return a 'not implemented' to SCO

        if hasattr(result, 'error_code'):
            # it's an error
            error_code = result.error_code
            value = result.value
        else:
            # it's a success with value
            error_code = 0
            value = result

        return {'result': 'success', 'error_code': error_code, 'value': value}

    def load_resource(self, resource_path):
        """
        Gets the content of a resource
        """
        resource_content = pkg_resources.resource_string(__name__, resource_path)
        return unicode(resource_content)

    def get_launch_html(self):
        '''
        Returns the 'entry point' or launcher HTML file name for the SCO.
        Returns None if we couldn't find an entry point.
        '''

        try:
            tree = etree.parse(os.path.join(self.scorm_path, self.scorm_dir, 'tincan.xml'))
        except IOError:
            return None

        # root = tree.getroot()
        ns = {'t': 'http://projecttincan.com/tincan.xsd'}
        return tree.find('./t:activities/t:activity/t:launch', namespaces=ns).text

    def tc_statement_process(self, content):
        '''
        content: JSON statement. Doesn't need to be validated.

        TODO: this object must already be bound to a username'''

        # TODO verify that the user is authorised to add the requested statement - there is information about the user embedded in the content object.

        # TODO test what happens when a bogus input string goes in here. Probably need to catch an exception and reject the request.
        statement = json.loads(content)

        print 'statement ', statement

        # We're looking for specific statements that Articulate generate on quiz completion.
        # TODO verify that the keys exist before you access them

        if  'object' not in statement.keys() or 'verb' not in statement.keys() or 'result' not in statement.keys():
            print 'missing something'
            return

        object_id = statement['object']['id']
        verb = statement['verb']['id']

        # TODO we need to be able to differentiate between a quiz within a course and the entire course

        if verb in 'http://adlnet.gov/expapi/verbs/passed' or verb in 'http://adlnet.gov/expapi/verbs/passed':
            if 'score' not in statement['result'].keys():
                print 'missing score'
                return

            if 'context' not in statement.keys():
                print 'missing context'
                # print statement.keys()
                return

            k = statement['result']['score'].keys()
            if 'raw' not in k or 'max' not in k or 'min' not in k or 'scaled' not in k:
                print 'missing something in score'
                return

            scaled_result = statement['result']['score']['scaled']
            raw_result = statement['result']['score']['raw']
            max_result = statement['result']['score']['max']
            # min_result = statement['result']['score']['min']
            success_result = statement['result']['success']
            username = statement['context']['registration']

            # TODO check what the verb was

            # TODO SECURITY obviously, we are trusting the client to give us the correct username. This is strictly for testing only. You would be very silly to deploy this to the public Internet.

            print '*** user %s completed quiz %s with score %f (%f/%f). success=%s' % (username, object_id, scaled_result * 100.0, raw_result, max_result, statement['result']['success'])

            # self.rebind_noauth_module_to_user(username)

            # public the 'quiz attempted' message
            self.has_grade = True

            print 'publishing grade event'
            event = {
                'value': raw_result,
                'max_value': max_result,
                'user_id': username
            }

            self.runtime.publish(self, 'grade', event)

            print 'published grade event'

        # TODO still have to say who completed it so we can generate the edx event


        # print dir(self)
        # print 'tc_statement_process: my user is %s' % self.user
        # print content

        # assert False, 'TODO implement user check'

    def student_view(self, context=None):
        if self.scorm_dir is None:
            return Fragment(u"<h1>Error</h1><p>There should be content here, but the course creator has not configured it yet. Please let them know.</p><p>If you're the course creator, you need to go into edX Studio and hit Edit on this block. Choose a SCORM object and click Save. Then, the content should appear here.</p>")

        # TODO tincan.xml is not supposed to be downloadable from the public web. Does this close the hole where people could download it and find the test answers? How do the js/swf versions know what the correct answers are? Does this mean that we can never use Tin Can for anything 'secure' or worth real marks?
        # Partly. story.js appears to be obfuscated. This is obviously dependent on the tool generating content. story.js definitely needs to be readable from the client side.

        # TODO it might be nice to confirm that the content is actually present

        # The 'thirdparty=True' parameter allows CSRF-less requests to be made
        # to this endpoint. This is important as we don't directly control the
        # content that is running on the client machine. We therefore can't
        # modify it to fit Django's CSRF/auth system. We will have to perform
        # CSRF and authentication checks manually.
        endpoint = self.runtime.handler_url(self, 'tincan_req', thirdparty=True)

        # endpoint must always end with /
        if not endpoint.endswith('/'):
            endpoint = '%s/' % endpoint

        print self.scope_ids

        # TODO review use of registration/activity_id/auth
        param_str = urllib.urlencode({
            'endpoint': endpoint,
            # 'csrftoken': csrf(
            # 'username': 'thisistheusername',
            # 'foo': 'bar',
            'auth': 'OjFjMGY4NTYxNzUwOGI4YWY0NjFkNzU5MWUxMzE1ZGQ1',
            # 'actor': '{"name": ["First Last"], "mbox": ["mailto:firstlast@mycompany.com"]}',
            # 'activity_id': '61XkSYC1ht2_course_id',
            'activity_id': 'this_is_activity_id',
            'registration': self.scope_ids.user_id
        })

        entry_point = self.get_launch_html()
        if entry_point is None:
            return Fragment(u"<h1>Error</h1><p>This content could not be displayed.</p><p>If you're the course creator, tincan.xml could not be loaded.</p>")

        url = '/scorm/%s/%s?%s' % (self.scorm_dir, self.get_launch_html(), param_str)

        html_str = pkg_resources.resource_string(__name__, "templates/tincan.html")
        frag = Fragment(unicode(html_str).format(self=self, url=url))

        return frag

    '''
    publish(block, event_type, event_data)
Publish an event.

For example, to participate in the course grade, an XBlock should set has_score to True, and should publish a grade event whenever the grade changes.

In this case the event_type would be grade, and the event_data would be a dictionary of the following form:

{
'value': <number>, 'max_value': <number>,
}

The grade event represents a grade of value/max_value for the current user.

block is the XBlock from which the event originates.

'''

    '''
    @XBlock.json_handler
    def scorm_set_value(self, data, suffix=''):
        """
        SCORM API handler to report data to the LMS

        Interestingly, even with the locks, if you read/write to/from
        self.scorm_data directly, you still have the race condition.

        Maybe something to do with the caching mechanism (which,
        it should be noted, this approach bypasses and thus does not
        benefit from). TODO: More research into why that doesn't work.
        """
        self.lock.acquire()
        try:
            scorm_data = self._field_data.get(self, "scorm_data")
        except KeyError:
            scorm_data = {}
        scorm_data.update(data)
        self._field_data.set(self, "scorm_data", scorm_data)
        self.lock.release()

    def publish_scorm_data(self, data):
        return
        '''

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("SCORM XBlock",
             # """<xb_scorm scorm_dir='USBS Referencing'/>"""),
             """<xb_scorm override_scorm_path='./scorm' scorm_dir='USBS Referencing Tincan'/>"""),
        ]


class SCORMXBlockStudioHack(SCORMXBlock):
    '''
    Wrapper for SCORMXBlock that shows the studio view (for development under
    the XBlock Workbench).

    FIXME: this is a nasty hack that probably isn't necessary. If you know how
    to do this better, please let me (ian@mutexlabs.com) know...

    Another alternative would be to pass in a flag in the scenario XML that
    forces studio display.
    '''

    def __init__(self, *args, **kwargs):
        self.scorm_path = os.path.abspath('./scorm/')
        SCORMXBlock.__init__(self, *args, **kwargs)

    def student_view(self, *args, **kwargs):
        # By default, SCORM content is served out of SCORM_PATH. In the Workbench this might not exist, so we override.
        return SCORMXBlock.studio_view(self, *args, **kwargs)

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("SCORM XBlock (Studio view)",
             # """<xb_scorm_studiohack scorm_dir='USBS Referencing'/>"""),
             """<xb_scorm_studiohack override_scorm_path='./scorm' scorm_dir='USBS Referencing Tincan'/>"""),
        ]
