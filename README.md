# What is it?
Experimental XBlock for hosting a SCORM content object. Currently it has built in trivial quiz for testing purposes, but eventually it will allow the user to upload an arbitrary SCORM zipfile.

# Resources
* See [here](http://scorm.com/scorm-explained/technical-scorm/run-time/) for an overview of the SCORM API.
* See the [issues page](https://github.com/usernamenumber/xb_scorm/issues) for (an incomplete list of) work that needs to be done.

# Contributing
1. Fork.
2. Comment on the issue related to the thing you want to fix, so others know you're working on it. If you want to do something that doesn't have an issue associated with it, create an issue. 
2. Work on each feature/issue in a separate branch
3. Submit pull request(s)

# Usage

1. [Install the XBlock](http://edx-developer-guide.readthedocs.org/en/latest/xblocks.html#testing). The module name for `advanced_modules` is `xb_scorm`.
2. Upload your SCORMs (see below)
3. Insert them into a course using Studio

# Uploading SCORMs

Right now, there is no nice GUI to do this. The XBlock looks under `/edx/app/edxapp/edx-platform/scorm` for potential SCORMs to display. They must be unzipped. The folder structure looks like:

    /edx/app/edxapp/edx-platform/scorm/
      |
      |--> some_scorm/
      |     |
      |     |--> ... some files ...
      |     |--> imsmanifest.xml
      |     |--> ... more files ...
      |
      |--> another_scorm/
            |
            |--> ... files ...
            |--> imsmanifest.xml

It looks for an `imsmanifest.xml` file inside the directory. It only looks one directory deep, so the above structure must be followed EXACTLY.

# Configuration

On Devstack, modify `/edx/app/edxapp/edx-platform/lms/urls.py`:

    if settings.DEBUG:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

        # SCORM content (NEW)
        urlpatterns += static('/scorm/', document_root='/edx/app/edxapp/edx-platform/scorm/')

        # in debug mode, allow any template to be rendered (most useful for UX reference templates)
        urlpatterns += url(r'^template/(?P<template>.+)$', 'debug.views.show_reference_template'),

Also modify `/edx/app/edxapp/edx-platform/mms/urls.py`:

    if settings.DEBUG:
        try:
            from .urls_dev import urlpatterns as dev_urlpatterns
            urlpatterns += dev_urlpatterns
        except ImportError:
            pass

        # SCORM content (NEW)
        from django.conf.urls.static import static
        urlpatterns += static('/scorm/', document_root='/edx/app/edxapp/edx-platform/scorm/')

In production, add to `/edx/app/nginx/sites-enabled/lms`:

    location ~ ^/scorm {
          root /edx/app/edxapp/edx-platform/;
    }

(All of this static location business will go away when someone gets time to fix it.)

If this filesystem location doesn't work for you, you can change it in `xb_scorm.py` near the top.

# Notes

As the content is simply 'dumped on a web server', any of it can be viewed by anyone who knows the URL. There are no permissions or security yet.
