"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, BlockScope, String, Dict, Field
import xblock.fields
from xblock.fragment import Fragment
from xblock.runtime import KeyValueStore

# BHS additions
import sys
import lxml.etree, time
import os.path
from cStringIO import StringIO
from threading import Lock
import json
import copy
import inspect


from xblock.fields import NO_CACHE_VALUE,  EXPLICITLY_SET, NO_GENERATED_DEFAULTS

class XblockSCORM(XBlock):
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

    def student_view(self,context=None):
        scorm_dir = os.path.join("static","scorm","exe1")
        scorm_index = os.path.join(scorm_dir,"index.html")
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
        
        html = lxml.etree.tostring(root_el,encoding=unicode,method="html")
        frag = Fragment(html)
        for fn in js_filenames:
            frag.add_javascript(self.resource_string(os.path.join(scorm_dir,fn)))
        for fn in css_filenames:
            frag.add_css(self.resource_string(os.path.join(scorm_dir,fn)))
        #frag.add_javascript(self.resource_string("static/js/src/scorm-api-wrapper/src/JavaScript/SCORM_API_wrapper.js"))
        frag.add_javascript(self.resource_string("static/js/src/xb_scorm.js"))
        frag.initialize_js('XblockSCORM')
        
        #import pdb; pdb.set_trace()
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
            scorm_data = self._field_data.get(self,"scorm_data")
        except KeyError:
            scorm_data = {}
        scorm_data.update(data)
        self._field_data.set(self,"scorm_data", scorm_data)
        self.lock.release()

    @XBlock.json_handler
    def scorm_get_value(self, data, suffix=''):
        """
        SCORM API handler to get data from the LMS
        """
        return self.scorm_data
        
    @XBlock.json_handler
    def scorm_clear(self,data,suffix=""):
        """
        Custom (not in SCORM API) function for emptying xblock scorm data
        """
        del(self.scorm_data)
        
    @XBlock.json_handler
    def scorm_dump(self,data,suffix=""):
        """
        Custom (not in SCORM API) function for viewing xblock scorm data
        """
        return self.scorm_data

    @XBlock.json_handler
    def scorm_test(self,data,suffix=""):
        """
        Custom (not in SCORM API) function for testing frequent writes in a single instance.
        """
        del(self.scorm_data)
        for k,v in data:
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

    def publish_scorm_data(self,data):
        return
        

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("XblockSCORM",
             """<vertical_demo>
                <xb_scorm/>
                </vertical_demo>
             """),
        ]
        
if __name__ == "__main__":
    print "DONE"
