"""TO-DO: Write a description of what this XBlock is."""

import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, String, Dict
import xblock.fields
from xblock.fragment import Fragment

# BHS additions
import lxml.etree, time
import os.path
from cStringIO import StringIO
from threading import Lock
import json




from xblock.fields import NO_CACHE_VALUE,  EXPLICITLY_SET, NO_GENERATED_DEFAULTS

class LoggingDict(Dict):
    
    lock = Lock()
     
    def __set__(self,xblock,value):
        #import pdb; pdb.set_trace()
        # Mark the field as dirty and update the cache:
        stamp = time.time()
        print "\n[%s]: __set__ for %s" % (stamp,xblock)   
        print "[%s]:    GIVEN: %s" % (stamp,value)
        super(LoggingDict,self).__set__(xblock,value)
        print "[%s]:    END: %s" %   (stamp,xblock) 
       
   # def __get__(self, xblock,xblock_class):
   #     stamp = time.time()
   #     print "\n[%s]: __get__ for %s" % (stamp,xblock)  
   #     val = super(self.__class__,self).__get__(xblock,xblock_class)
   #     print "[%s]:    RETURN: %s" % (stamp,val)
   #     return val
        
    def __get__(self, xblock, xblock_class):
            
        """
        Gets the value of this xblock. Prioritizes the cached value over
        obtaining the value from the _field_data. Thus if a cached value
        exists, that is the value that will be returned.
        """
        stamp = time.time()
        print "\n[%s]: __get__" % (stamp)  
        #try:
        #    ret = super(LoggingDict,self).__get__(xblock,xblock_class)
        #except Exception,e:
        #    import traceback
        #    traceback.print_exc(file=sys.stdout)
        #    print "[%s]:    EXCEPTION: %s" % (stamp,e)
        #print "[%s]:    RETURN: %s" % (stamp,ret)
        #return ret
        #
        # pylint: disable=protected-access
        if xblock is None:
            print "[%s]:    RETURN (xblock is None): %s" % (stamp,self)
            return self

        value = self._get_cached_value(xblock)
        print "[%s]:    VAL (cache): %s" % (stamp,value)
        if value is NO_CACHE_VALUE:
            try:
                if xblock._field_data.has(xblock, self.name):
                    value = self.from_json(xblock._field_data.get(xblock, self.name))
                    print "[%s]:    VAL (field_data): %s" % (stamp,value)
                elif self.name not in NO_GENERATED_DEFAULTS:
                    # Cache default value
                    try:
                        value = self.from_json(xblock._field_data.default(xblock, self.name))
                        print "[%s]:    VAL (field_data default): %s" % (stamp,value)
                    except KeyError:
                        value = self.default
                        print "[%s]:    VAL (self default 1): %s" % (stamp,value)
                else:
                    value = self.default
                    print "[%s]:    VAL (self default 2): %s" % (stamp,value)
                self._set_cached_value(xblock, value)
            except:
                import traceback, sys
                traceback.print_exc(file=sys.stdout)

        # If this is a mutable type, mark it as dirty, since mutations can occur without an
        # explicit call to __set__ (but they do require a call to __get__)
        if self.MUTABLE:
            print "[%s]:    DIRTY" % (stamp)
            self._mark_dirty(xblock, value)
        
        print "[%s]:    RETURN: %s" % (stamp,value)
        return value
        
    def _set_cached_value(self, xblock, value):
        """Store a value in the xblock's cache, creating the cache if necessary."""
        # pylint: disable=protected-access
        stamp = time.time()
        print "\n[%s]    ACQUIRING LOCK on %s" % (stamp,self.lock)
        self.lock.acquire()
        key = self.name
        print "\n[%s]: _set_cached_value" % stamp
        print "[%s]:    GIVEN: %s" % (stamp,value)
        if not hasattr(xblock, '_field_data_cache'):
            print "[%s]:    CREATE new cache" % stamp
            xblock._field_data_cache = {}  
        
        print "[%s]:    STARTING CACHE: %s" % (stamp,xblock._field_data_cache)
        if not hasattr(xblock._field_data_cache,key):
            print "[%s]:    CREATE new cache entry for %s" % (stamp,key)
            xblock._field_data_cache[key] = {}
        xblock._field_data_cache[key].update(value)
        print "[%s]:    CACHE (update) is now: %s" % (stamp,xblock._field_data_cache)
        print "\n[%s]    RELEASING LOCK on %s" % (stamp,self.lock)
        self.lock.release()
        


class XblockSCORM(XBlock):
    """
    XBlock wrapper for SCORM content objects
    """
    #scorm_data = LoggingDict(
    #    default = {},
    #    scope=Scope.user_state,
    #    help="Temporary storage for SCORM data",
    #)     
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
        
        
    def publish_scorm_data(self,data):
        #if self.scorm_data.has_key('cmi.core.score.raw') and self.scorm_data.has_key('cmi.core.score.max'):
        #    event_data = {
        #        "value" : self.scorm_data['cmi.core.score.raw'],
        #        "max_value" : self.scorm_data['cmi.core.score.max'],
        #    }    
        #    print "Publishing %s" % event_data
        #    self.runtime.publish(self,'grade',event_data)
        # TODO: do something if required info isn't present?    
        pass
        

    @XBlock.json_handler
    def scorm_set_value(self, data, suffix=''):
        """
        Store data reported by the SCORM object
        """
        print "\n[%s]: scorm_set_value for %s" % (stamp,xblock)
        in_data = str(data)
        print "[%s]:     GIVEN: %s" % (stamp,in_data)
        for k, v in data.iteritems():
            self.scorm_data[k] = v
        scorm_str = str(self.scorm_data)
        print "[%s]:     AFTER UPDATE:  %s" % (stamp,scorm_str)
        return self.scorm_data


    @XBlock.json_handler
    def scorm_get_value(self, data, suffix=''):
        """
        Store data reported by the SCORM object
        """
        return self.scorm_data


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
        del(self.scorm_data)
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
