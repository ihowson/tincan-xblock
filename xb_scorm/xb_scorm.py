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

# from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

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
    tc_activities_state = String(default='', scope=Scope.user_state)




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

    # @ensure_csrf_cookie
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
    # @XBlock.json_handler
    # @csrf_exempt
    def tincan_req(self, data, suffix=''):
        '''
        JSON endpoint for Tin Can client requests.
        All methods are multiplexed through this function.
        '''

        if data.method != 'POST':
            assert False, 'unknown method %s' % data.method

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

    def tincan_handle(self, method, suffix, post):
        '''
        Returns a JSON string for a successful 200 request. Raises a
        webob.exc.HTTPException in case of error (or non-200 response).

        post: the HTTP POST parameters
        '''

        # demux
        print 'method %s suffix %s' % (method, suffix)
        if suffix == 'activities/state':
            if method == 'GET':
                return self.tc_activities_state
        elif suffix == 'statements':
            if method == 'PUT':
                # if it already exists and is different, return 409 Conflict. If same, return 204 No Content.
                # if not already exists, store it and return 204 No Content
                # TODO does 'different' means logically (at JSON level) or identical at byte level?

            from pprint import pprint
            print '--- content'
            pprint(post['content'])

            print '--- statementId'
            pprint(post['statementId'])

            # statement_id = params['statementId']
            # print 'sid %s, body %s' % (statement_id, body)
            # print 

            # TODO implement 409 Conflict response where appropriate
            pass
        '''
        elif suffix == 'activities/profile' and method == 'POST':
            pass
        elif suffix == 'agent/profile' and method == 'POST':
            pass
            '''

        print 'tincan_handle: unhandled method %s %s' % (method, suffix)
        return webob.exc.HTTPNotImplemented()  # FIXME: change this to 'unknown method' when appropriate (when you've implemented a good number of endpoints)

    def handle(self, handler_name, request, suffix=''):
        # print handler_name, request, suffix
        print 'handler: handler_name'
        return super(SCORMXBlock, self).handle(handler_name, request, suffix)

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

        # print 'FIXME STUB: sco_req %s' % data
        # self.scorm_dir = data.get('scorm_dir')

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
        '''

        # TODO put some error checking around this, especially if tincan.xml is missing
        print os.path.join(self.scorm_path, self.scorm_dir, 'tincan.xml')
        try:
            tree = etree.parse(os.path.join(self.scorm_path, self.scorm_dir, 'tincan.xml'))
        except IOError:
            assert False, 'TODO NOT IMPLEMENTED: handle missing tincan.xml'

        # root = tree.getroot()
        ns = {'t': 'http://projecttincan.com/tincan.xsd'}
        return tree.find('./t:activities/t:activity/t:launch', namespaces=ns).text

    # @ensure_csrf_cookie
    def student_view(self, context=None):
        if self.scorm_dir is None:
            return Fragment(u"<h1>Error</h1><p>There should be content here, but the course creator has not configured it yet. Please let them know.</p><p>If you're the course creator, you need to go into edX Studio and hit Edit on this block. Choose a SCORM object and click Save. Then, the content should appear here.</p>")

        # TODO tincan.xml is not supposed to be downloadable from the public web. Does this close the hole where people could download it and find the test answers? How do the js/swf versions know what the correct answers are? Does this mean that we can never use Tin Can for anything 'secure' or worth real marks?
        # Partly. story.js appears to be obfuscated. This is obviously dependent on the tool generating content. story.js definitely needs to be readable from the client side.

        # TODO it might be nice to confirm that the content is actually present

        endpoint = self.runtime.handler_url(self, 'tincan_req')
        print endpoint

        # print dir(self)
        # print context

        # TODO: you need to think VERY CAREFULLY about how to handle CSRF/auth here. CSRF checks are currently DISABLED on the endpoint.
        # Hopefully this is something that the TinCan folks have already thought about, so you might just need to read the spec properly to find out how to solve it.
        # FIXME: csrf isn't working through edX right now (the cookies/csrf objs aren't visible. You've tweaked workbench to use csrf_exempt on the handler, but this might not work in edx proper. Consider monkeypatching edx to allow an exemption here?
        # If you pass csrftoken in to the URL params then it passes back happily, but it's not working for some reason
        # Already burned half a day on this.
        param_str = urllib.urlencode({
            'endpoint': endpoint,
            # 'csrftoken': csrf(
            # 'foo': 'bar',
            # 'auth': 'OjFjMGY4NTYxNzUwOGI4YWY0NjFkNzU5MWUxMzE1ZGQ1',
            # 'actor': '{"name": ["First Last"], "mbox": ["mailto:firstlast@mycompany.com"]}',
            # 'activity_id': '61XkSYC1ht2_course_id',
            # 'registration': '760e3480-ba55-4991-94b0-01820dbd23a2'
        })

        # print param_str

        url = '/scorm/%s/%s?%s' % (self.scorm_dir, self.get_launch_html(), param_str)

        html_str = pkg_resources.resource_string(__name__, "templates/tincan.html")
        frag = Fragment(unicode(html_str).format(self=self, url=url))

        frag.add_javascript(self.resource_string("public/csrf.js"))
        # frag.initialize_js('csrf_init')
        # frag.add_javascript(self.resource_string("public/rte.js"))
        # frag.add_javascript(self.resource_string("public/SCORM_API_wrapper.js"))
        # frag.add_javascript(self.resource_string("public/frame.js"))
        # frag.initialize_js('SCORMXBlock')

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

    @XBlock.json_handler
    def scorm_get_value(self, data, suffix=''):
        """
        SCORM API handler to get data from the LMS
        """
        return self.scorm_data

    @XBlock.json_handler
    def scorm_clear(self, data, suffix=""):
        """
        Custom (not in SCORM API) function for emptying xblock scorm data
        """
        del(self.scorm_data)

    @XBlock.json_handler
    def scorm_dump(self, data, suffix=""):
        """
        Custom (not in SCORM API) function for viewing xblock scorm data
        """
        return self.scorm_data

    @XBlock.json_handler
    def scorm_test(self, data, suffix=""):
        """
        Custom (not in SCORM API) function for testing frequent writes in a single instance.
        """
        del(self.scorm_data)
        for k, v in data:
            self.scorm_data[k] = v

     ##
     # The rest of these aren't really implemented yet
     ##
    @XBlock.json_handler
    def scorm_commit(self, data, suffix=""):
        """
        SCORM API handler to permanently store data in the LMS
        """
        return self.publish_scorm_data(data)

    @XBlock.json_handler
    def scorm_finish(self, data, suffix=""):
        """
        SCORM API handler to wrap up communication with the LMS
        """
        return self.publish_scorm_data(data)

    def publish_scorm_data(self, data):
        return

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("SCORM XBlock",
             # """<xb_scorm scorm_dir='USBS Referencing'/>"""),
             """<xb_scorm override_scorm_path='./scorm' scorm_dir='USBS Referencing Tincan'/>"""),
        ]

    # SCORM 2004 data model
    class SCORMError(object):
        def __init__(self, error_code, value=''):
            self.error_code = error_code
            self.value = value

    def get(self, key):
        if key == 'cmi.completion_status':
            return self.cmi_completion_status
        elif key == 'cmi.mode':
            return 'normal'
        elif key == 'cmi.success_status':
            return 'unknown'
        elif key == 'cmi.suspend_data':
            return SCORMError(403)
        elif key == 'cmi.scaled_passing_score':
            assert False, 'TODO you need to modify cmi.success_status to handle this value'
        elif key == 'cmi.completion_threshold':
            assert False, 'TODO you need to modify cmi.completion_status to handle this value'
        else:
            print "SCORM2004::get('%s'): unknown key" % key
            assert False, 'get return not implemented'

    def set(self, key, value):
        if key == 'cmi.completion_status':
            self.cmi_completion_status = value  # TODO check the value we're trying to write
        elif key == 'cmi.exit':  # write-only
            if value == 'suspend':
                self.cmi_entry = 'resume'
            # elif value == 'logout':
                # self.cmi_entry = '
            else:
                assert False, 'TODO not implemented verb %s for cmi.exit' % value
        elif key == 'cmi.scaled_passing_score':
            assert False, 'TODO you need to modify cmi.success_status to handle this value'
        elif key == 'cmi.completion_threshold':
            assert False, 'TODO you need to modify cmi.completion_status to handle this value'
        # elif key == 'cmi.suspend_data':
            # assert False, 'TODO suspend_data'
        else:
            print "SCORM2004::set('%s'): unknown key" % key
            assert False, 'set return not implemented'


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
