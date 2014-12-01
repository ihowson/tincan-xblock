function SCORMXBlock(runtime, element) {
    tspInit(
        window,
        runtime.handlerUrl(element, 'sco_req'),
        '', //'SCORM_ID.'. This has to be unique per each scorm you serve
        $.cookie('csrftoken'),
        function(progress) {
            //this will be called whenever student makes a progress in test.
            console.log('progress: ', progress);
        }
    );

    pipwerks.SCORM.init();
}