"""
XBlock to display SCORM content.
Right now, this is targeting the SCORM 2014 API.

FIXME: No consideration has been given to security. Don't let untrusted staff use this.

I'm targeting Articulate Storyline first per the document at https://en-uk.articulate.com/tincanapi/
"""

# The path that SCORM content is stored in
# FIXME: nasty
DEFAULT_SCORM_PATH = '/edx/app/edxapp/scorm'

from datetime import datetime
import json
from lxml import etree
import os
import os.path
import pkg_resources
from threading import Lock
import urllib
import uuid

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

    has_score = True
    icon_class = 'video'
    weight = None  # TODO: this field isn't mentioned in any documentation, but seems to be necessary

    scorm_dir = String(help="Directory that the SCORM content object is stored in", default=None, scope=Scope.settings)

    # FIXME: dodgy hack to ease debugging under Workbench
    override_scorm_path = String(default=None, scope=Scope.settings)

    lock = Lock()
    scorm_data = Dict(
        scope=Scope.user_state,
        help="Temporary storage for SCORM data",
    )

    display_name = String(
        default="Lecture", scope=Scope.settings,
        help="Display name"
    )

    def max_score(self):
        """The maximum raw score of our problem."""
        # TODO: we should check tincan.xml for this value
        return 100

    # Tin Can data model
    tc_activities_state = Dict(default={}, scope=Scope.user_state)  # stateId -> JSON document
    tc_statements = Dict(default={}, scope=Scope.user_state)  # statementId -> JSON document

    scorm_path = DEFAULT_SCORM_PATH

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

        # TODO we seem to be getting the user already (presumably through the
        # sessionid cookie). There's definitely no CSRF protection, though. We
        # can pass that in the cookie or through the JSON requests and verify
        # it manually.
        assert self.scope_ids is not None and self.scope_ids.user_id is not None, 'no scope id'

        if data.method not in ['POST', 'PUT', 'GET']:
            raise webob.exc.HTTPMethodNotAllowed('%s not allowed' % data.method)

        method = None

        # TODO FIXME IMPORTANT: check csrf token explicitly here
        print 'FIXME: no CSRF check on tincan_req yet. user=%s' % self.scope_ids.user_id

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

        We assume that the user has been authenticated and CSRF checked.

        post: the HTTP POST parameters
        '''

        # demux
        # print 'method %s %s' % (method, suffix)

        # Articulate HTML5 player sometimes sends '/' suffixes like 'statements/'
        if suffix.endswith('/'):
            suffix = suffix[:-1]

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
                raise webob.exc.HTTPNoContent()
        elif suffix == 'statements':
            if method == 'PUT':
                # TODO: I'm not clear on what the difference between PUT and POST is at this stage. Storyline only seems to be generating PUT.
                self.requireParams(post, ['statementId', 'content'])

                sid = post['statementId']
                content = post['content']

                # does it already exist?
                if sid in self.tc_statements.keys():
                    # If it's different, return 409 Conflict. If same, return 204 No Content.
                    # TODO: would be better to check logical JSON equality rather than byte equality
                    # TODO: if we're modifying fields (e.g. by adding 'id', 'stored' and 'timestamp', how does that affect our idea of equality? Do we just check to see that the fields that were specified by the AP were equal? Surely the spec has more detail on what 'equal' means.
                    if self.tc_statements[sid] == content:
                        raise webob.exc.HTTPNoContent()
                    else:
                        raise webob.exc.HTTPConflict()
                else:
                    # we're going to store it as a new statement, but we might need to add some fields first

                    # parse it back to a Python object so we can manipulate it
                    statement = json.loads(content)
                    # TODO: error checking in case the statement was not parseable. If not, return HTTPBadRequest

                    # check that all required fields are present
                    if not all([key in statement.keys() for key in ['actor', 'verb', 'object']]):
                        raise webob.exc.HTTPBadRequest('missing a key')

                    if 'id' not in statement.keys():
                        statement['id'] = str(uuid.uuid4())  # TODO: check the UUID format required; the spec has pending clarifications

                    # set 'stored'
                    statement['stored'] = datetime.now().isoformat()

                    if 'timestamp' not in statement.keys():
                        statement['timestamp'] = statement['stored']

                    # convert back to JSON
                    content = json.dumps(statement)

                    # store it
                    self.tc_statements[sid] = content

                    # TODO: eventually, we can process these asynchronously
                    # using celery so we don't block the web server. For now,
                    # this is easier (but slower).
                    self.tc_statement_process(content)

                    raise webob.exc.HTTPNoContent()
            elif method == 'GET':
                pass
                # TODO

        print 'tincan_handle: unhandled method %s %s' % (method, suffix)
        raise webob.exc.HTTPNotImplemented()  # FIXME: change this to 'unknown method' when appropriate (when you've implemented a good number of endpoints)

    def load_resource(self, resource_path):
        """
        Gets the content of a resource
        """
        resource_content = pkg_resources.resource_string(__name__, resource_path)
        return unicode(resource_content)

    def get_launch_html(self):
        '''
        Returns the 'entry point' or launcher HTML file name for the SCO/AP.
        Returns None if we couldn't find an entry point.
        '''

        try:
            tree = etree.parse(os.path.join(self.scorm_path, self.scorm_dir, 'tincan.xml'))
        except IOError:
            return None

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

        if 'object' not in statement.keys() or 'id' not in statement['object'].keys() or 'verb' not in statement.keys() or 'result' not in statement.keys():
            print 'missing something'
            return

        object_id = statement['object']['id']
        verb = statement['verb']['id']

        # TODO we need to be able to differentiate between a quiz within a course and the entire course

        QUIZ_COMPLETE_VERBS = [
            'http://adlnet.gov/expapi/verbs/passed',
            'http://adlnet.gov/expapi/verbs/failed'
        ]

        if verb in QUIZ_COMPLETE_VERBS:
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

            # TODO check what the verb was

            print '*** user id %s completed quiz %s with score %f (%f/%f). success=%s' % (self.scope_ids.user_id, object_id, scaled_result * 100.0, raw_result, max_result, statement['result']['success'])

            # update the user's grades
            event = {
                'value': raw_result,
                'max_value': max_result,
            }

            # On my devstack, 'runtime' is sufficient. In (slightly older) production, this needs to be xmodule_runtime.
            # 12 hours to figure this out, but at least I know how the entire grade submission chain works now...
            self.xmodule_runtime.publish(self, 'grade', event)

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

        # TODO review use of registration/activity_id/auth
        param_str = urllib.urlencode({
            'endpoint': endpoint,
            # 'csrftoken': csrf(
            # 'username': 'thisistheusername',
            # 'foo': 'bar',
            # 'auth': 'OjFjMGY4NTYxNzUwOGI4YWY0NjFkNzU5MWUxMzE1ZGQ1',
            # 'actor': '{"name": ["First Last"], "mbox": ["mailto:firstlast@mycompany.com"]}',
            # 'activity_id': '61XkSYC1ht2_course_id',
            # 'activity_id': 'this_is_activity_id',
            # 'registration': self.scope_ids.user_id
        })

        entry_point = self.get_launch_html()
        if entry_point is None:
            return Fragment(u"<h1>Error</h1><p>This content could not be displayed.</p><p>If you're the course creator, tincan.xml could not be loaded.</p>")

        url = '/scorm/%s/%s?%s' % (self.scorm_dir, self.get_launch_html(), param_str)

        html_str = pkg_resources.resource_string(__name__, "templates/tincan.html")
        frag = Fragment(unicode(html_str).format(self=self, url=url))

        return frag

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
