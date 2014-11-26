"""
XBlock to display SCORM content.
Right now, this is targeting the SCORM 2014 API.

FIXME: No consideration has been given to security. Don't let untrusted staff use this.
"""

# The path that SCORM content is stored in
# FIXME: nasty
SCORM_PATH = '/edx/app/edxapp/edx-platform/scorm'

import lxml.etree
import os
import os.path
import pkg_resources
from threading import Lock

from xblock.core import XBlock
from xblock.fields import Scope, BlockScope, String, Dict, Field
from xblock.fragment import Fragment
from xblock.runtime import KeyValueStore


class SCORMXBlock(XBlock):
    """
    XBlock wrapper for SCORM content objects
    """
    lock = Lock()
    scorm_data = Dict(
        scope=Scope.user_state,
        help="Temporary storage for SCORM data",
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def studio_view(self, context=None, scorm_path=SCORM_PATH):
        try:
            try:
                ls = os.listdir(scorm_path)
            except OSError, e:
                return Fragment(u"ERROR: couldn't read SCORM directory (%s). The full error is '%s'." % (scorm_path, e))

            # make a list of available SCORMs
            scorms = []
            for dirname in ls:
                # check if there is a manifest
                if os.path.isfile(os.path.join(scorm_path, dirname, 'imsmanifest.xml')):
                    scorms.append(dirname)

            print scorms  # FIXME REMOVE
            frag = Fragment(content=u'<h2>Available SCORMs</h2><ul>')

            for s in scorms:
                frag.add_content(u'<li>%s</li>' % s)

            frag.add_content(u'</ul>')
        except Exception, e:
            # This is horrible and nasty, but this way we actually get some debug info.
            import traceback
            print traceback.print_exc()
            frag = Fragment(e.exc_info())

        return frag

    def load_resource(self, resource_path):
        """
        Gets the content of a resource
        """
        resource_content = pkg_resources.resource_string(__name__, resource_path)
        return unicode(resource_content)

    def student_view(self, context=None):
        scorm_dir = os.path.join("static", "scorm", "exe1")
        scorm_index = os.path.join(scorm_dir, "index.html")
        scorm_html = self.resource_string(scorm_index)
        root_el = lxml.etree.HTML(str(scorm_html))
        js_filenames = []
        for js_el in root_el.xpath("//script[@type='text/javascript' and @src != '']"):
            js_filenames.append(js_el.get("src"))
            js_el.getparent().remove(js_el)

        css_filenames = []
        for css_el in root_el.xpath("//link[@rel='stylesheet' and @href != '']"):
            css_filenames.append(css_el.get("href"))
            css_el.getparent().remove(css_el)

        html = lxml.etree.tostring(root_el, encoding=unicode, method="html")
        frag = Fragment(html)
        for fn in js_filenames:
            frag.add_javascript(self.resource_string(os.path.join(scorm_dir, fn)))
        for fn in css_filenames:
            frag.add_css(self.resource_string(os.path.join(scorm_dir, fn)))
        #frag.add_javascript(self.resource_string("static/js/src/scorm-api-wrapper/src/JavaScript/SCORM_API_wrapper.js"))
        frag.add_javascript(self.resource_string("static/js/src/xb_scorm.js"))
        frag.initialize_js('SCORMXBlock')

        return frag

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
             """<xb_scorm/>"""),
        ]


class SCORMXBlockStudioHack(SCORMXBlock):
    '''
    Wrapper for SCORMXBlock that shows the studio view (for development under
    the XBlock Workbench).

    FIXME: this is a nasty hack that probably isn't necessary. If you know how
    to do this better, please let me (ian@mutexlabs.com) know...
    '''

    def student_view(self, *args, **kwargs):
        # By default, SCORM content is served out of SCORM_PATH. In the Workbench this might not exist, so we override.
        return SCORMXBlock.studio_view(self, scorm_path=os.path.abspath('./scorm/'), *args, **kwargs)

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("SCORM XBlock (Studio view)",
             """<xb_scorm_studiohack/>"""),
        ]
