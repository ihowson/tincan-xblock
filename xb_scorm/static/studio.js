function SCORMStudioXBlock(runtime, element) {
  $(element).find('.save-button').bind('click', function() {
    var handlerUrl = runtime.handlerUrl(element, 'studio_submit');
    var data = {
      scorm_dir: $(element).find('input[name=scorm_dir]:checked').val()
    };
    $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
      window.location.reload(false);
    });
  });

  // $(element).find('.cancel-button').bind('click', function() {
  //   runtime.notify('cancel', {});
  // });
}
