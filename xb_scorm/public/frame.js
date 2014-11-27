function scorm_init(runtime, element) {
    tspInit(
        window,
        //edx.getStorage(), // null, //window.localStorage, // we always want to use server storage
        //this has to be unique per each scorm you serve
        '', //'SCORM_ID.',
        'TODO csrf_token goes here',
        function(progress) {
            //this will be called whenever student makes a progress in test.
            console.log(progress);
        }
    );

    pipwerks.SCORM.init();
}