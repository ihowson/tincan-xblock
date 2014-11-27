var rteErrorCode = '0';

var LOGGING = true;

var g_csrf_token = null;

function ajaj(object) {
    console.log("STUB AJAJ: ", object);
    return null; 
    
    var xhr = new XMLHttpRequest();
    json_request = JSON.stringify(object);

    // Unfortunately, we use synchronous requests. This is because the SCORM RTE expects us to use the return value to convey information; there's no way to connect an asynchronous block to it.

    xhr.open("POST", "/scorm/json", false);
    xhr.setRequestHeader("X-CSRFToken", g_csrf_token);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(json_request);

    // synchronous code
    if (xhr.status == 200) {
        // console.log("response = " + xhr.responseText);
        // parse it and return it to the caller

        var response_object = JSON.parse(xhr.responseText);
        return response_object;
    } else {
        console.log('ajaj error code ' + xhr.status);
        return null;
        // TODO this breaks calling code
    }
}

function tspInit(window, prefix, csrf_token, callback) {
    console.log('tspInit');
    
    // prefix = typeof prefix !== 'undefined' ? prefix : '';
    // callback = typeof callback !== 'undefined' ? callback : console.log;
    
    var api = {};
    g_csrf_token = csrf_token;

    // window.API = api;
    window.API_1484_11 = api;

    // Most functions are supposed to set the error code.

    api.Initialize = function() {
        console.log('LMSInitialize');

        console.log('FIXME STUB Initialize');
        return true;


        
        // TODO probably not much to do here, maybe verify that the user auth is correct before they get started

        // verify server connectivity
        ret = ajaj({'method': 'init'});

        if (ret === null) {
            // something went wrong
            return false;
        }

        rteErrorCode = ret['errorCode'];
        if (rteErrorCode == '0') {
            return true; // true denotes success
        } else {
            return false;
        }
    }

    // window.API.LMSTerminate = function() {
    api.Terminate = function() {
        console.log('LMSTerminate');
        // TODO you're supposed to commit to the database here, but that probably won't be necessary
        rteErrorCode = '0';
        return true; // true denotes success
    }

    /*
    window.scormStatus = {
            lesson_status: '',
            score_raw: 0,
            score_max: 100,
            score_min: 0,
            session_time: 0,
            detailed_answers: {}
    };
    */
    
    api.GetValue = function(varname) {
        ret = ajaj({'method': 'getValue', 'name': varname});

        if (ret === null) {
            // something went wrong
            rteErrorCode = '301'; // General Get Failure
        } else {
            rteErrorCode = ret['errorCode'];
        }

        if (rteErrorCode == '0') {
            var val = ret['value'];
            console.log('LMSGetValue', varname, '=', val);
            return val;
        } else {
            console.log('LMSGetValue failed ' + rteErrorCode);
            return '';
        }
        /* REMOVED UNTIL WE UNDERSTAND THIS
        varname = prefix + varname;
        if (ret == null && (varname.indexOf('_count', this.length - '_count'.length) !== -1)) {
            console.log("TODO: there is magic handling of _count variables for some reason");
            ret = 0;
            storage.setItem(varname, ret);
        }
        */
        // if you get the value successfully, return the value
        // if you fail, return an empty string and set the error code appropriately
    }
    
    // window.API.LMSSetValue = function(varname, varvalue) {
    api.SetValue = function(varname, varvalue) {
        varname = prefix + varname;
    
        // TODO return 'true' if success or 'false' and set error code if it fails

        /* REMOVED UNTIL WE UNDERSTAND THIS
        var m = varname.match(/([0-9]+)\.cmi\.interactions\.([0-9]+)\.id/);
        if (m != null) {
            storage.setItem('{{scorm.id}}.cmi.interactions._count', parseInt(m[2]) + 1);
        }
    
        m = varname.match(/([0-9]+)\.cmi\.interactions\.([0-9]+)\.result/);
        if (m != null) {
            var key = storage.getItem(prefix + 'cmi.interactions.' + parseInt(m[2]) + '.id');
            window.scormStatus.detailed_answers[key] = varvalue;
        }
    
        if (varname == prefix + 'cmi.core.lesson_status')
            window.scormStatus.lesson_status = varvalue;
        if (varname == prefix + 'cmi.core.score.raw')
            window.scormStatus.score_raw = varvalue;
        if (varname == prefix + 'cmi.core.score.max')
            window.scormStatus.score_max = varvalue;
        if (varname == prefix + 'cmi.core.score.min')
            window.scormStatus.score_min = varvalue;
        if (varname == prefix + 'cmi.core.session_time')
            window.scormStatus.session_time = varvalue;
        */
    
        rteErrorCode = '101'; // general exception, not implemented
        console.log('LMSSetValue', varname, '=', varvalue);
    }
    
    api.Commit = function() {
        // we aren't bothering with explicit commits; everything is a commit
        console.log('LMSCommit');
        //saving to API
        // TODO don't understand the following line
        // callback(window.scormStatus);
        rteErrorCode = '0';
        return true; 
    }
    
    api.Finish = function() {
        rteErrorCode = '0';
        console.log('LMSFinish');
    }
    
    api.GetLastError = function() {
        console.log('LMSGetLastError: ' + rteErrorCode);
        return rteErrorCode;
    }
    
    api.GetErrorString = function(code) {
        console.log('LMSGetErrorString ' + code);

        // TODO you're supposed to return a textual description of the error string

        return '';
    }
    
    api.GetDiagnostic = function() {
        console.log('LMSGetDiagnostic');
        // LMS specific. Don't bother right now.
    }
}
