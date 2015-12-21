<?xml version="1.0" encoding="utf-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">

    <head>

        <meta content="text/html; charset=utf-8" http-equiv="content-type" />
        <title>PyPI - the Python Package Index : Python Package Index</title>
        <link rel="stylesheet" href="/static/styles/styles.css" type="text/css" />
        <link rel="stylesheet" href="/static/css/pypi.css" type="text/css" />
    </head>

    <body>
        <!--  Logo  -->
        <h1 id="logoheader">
            <a accesskey="1" href="http://www.python.org" id="logolink">
                <img src="/static/images/python-logo.png" alt="homepage" border="0" id="logo" />
            </a>
        </h1>
        <div id="content-body">
            <div id="body-main">
                <div id="content">
                    <div id="breadcrumb">
                        <a href="/pypi">Package Index</a>
                    </div>
                    <div class="section">
                        <h1>PyPI - the Python Package Index</h1>
                        <p>The Python Package Index is a repository of software for the Python programming language. There are currently
                            <strong>{{CNTPKG}}</strong>
                            packages here.
                        </p>
                        <br clear="both" />
                        <table class="list">
                            <tbody>
                                <tr>
                                    <th>Updated</th>
                                    <th>Package</th>
                                    <th>Description</th>
                                </tr>
                                % tclass = 'even'
                                % for pkg, href, summary, ctime in links:
                                    % tclass = tclass == 'odd' and 'even' or 'odd'
                                    <tr class={{tclass}}>
                                        <td style="white-space: nowrap; text-align: center;">{{ctime}}</td>
                                        <td><a href="{{href}}">{{pkg}}</a></td>
                                        <td>{{summary}}</td>
                                    </tr>
                                % end
                                <tr>
                                    <td id="last" colspan="3">
                                </td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div id="footer">
                    <div id="credits">
                        <a href="http://python.org/pypi" title="Design inspired by http://python.org/pypi">Design inspired by http://python.org/pypi</a>
                    </div>
                    <a href="http://pypi.python.org/pypi/pypiserver">pypiserver</a> software.</p>
                    <br/>
                </div>
            </div>
        </div>


    </body>

    </html>
