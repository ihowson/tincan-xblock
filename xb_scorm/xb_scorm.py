"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, Dict
import xblock.fields
from xblock.fragment import Fragment

# BHS additions
import lxml.etree, time
import os.path
from cStringIO import StringIO

class XblockSCORM(XBlock):
    """
    XBlock wrapper for SCORM content objects
    """

    scorm_data = Dict(
        default = {},
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
        return frag
        
        
    def publish_scorm_data(self,data):
        if self.scorm_data.has_key('cmi.core.score.raw') and self.scorm_data.has_key('cmi.core.score.max'):
            event_data = {
                "value" : self.scorm_data['cmi.core.score.raw'],
                "max_value" : self.scorm_data['cmi.core.score.max'],
            }    
            print "Publishing %s" % event_data
            self.runtime.publish(self,'grade',event_data)
        # TODO: do something if required info isn't present?        
        

    @XBlock.json_handler
    def scorm_set_value(self, data, suffix=''):
        """
        Store data reported by the SCORM object
        """
        scorm_data = {}
        scorm_data["%s BEFORE SET %s" % (time.time(),data)] = str(self.scorm_data)
        print "\nset_value: given %s" % data
        for (var,val) in data.items():
            print "set_value:   Updating %s: %s" % (var,val)
            self.scorm_data[var] = val
        print "set_value: Updated %s\n" % self.scorm_data
        scorm_data["%s AFTER SET %s" % (time.time(),data)] =  str(self.scorm_data)
        return scorm_data
        

    @XBlock.json_handler
    def scorm_get_value(self, data, suffix=''):
        """
        Store data reported by the SCORM object
        """
        cmi_element = data
        if self.scorm_data.has_key(cmi_element):
            value = self.scorm_data[cmi_element]
        else: 
            value = ""
        return {cmi_element : value}


    @XBlock.json_handler
    def scorm_commit(self, data, suffix=""):
        """
        Publish SCORM scores to the LMS
        """
        self.publish_scorm_data(data)
        scorm_data = { "%s AFTER COMMIT" % time.time() : str(self.scorm_data) }
        return scorm_data
        
       
    @XBlock.json_handler
    def scorm_finish(self, data, suffix=""):
        self.publish_scorm_data(data)
        scorm_data = { "%s AFTER FINISH" % time.time() : str(self.scorm_data) }
        return scorm_data
        
    @XBlock.json_handler
    def scorm_clear(self,data,suffix=""):
        """
        Custom (not in SCORM API) function for emptying xblock scorm data
        """
        self.scorm_data.clear()
        return self.scorm_data
        
    @XBlock.json_handler
    def scorm_dump(self,data,suffix=""):
        """
        Custom (not in SCORM API) function for viewing xblock scorm data
        """
        return self.scorm_data
        

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
