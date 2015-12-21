<?xml version="1.0" encoding="utf-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">

    <head>

        <meta content="text/html; charset=utf-8" http-equiv="content-type" />
        <title>PyPI - the Python Package Index : Python Package Index</title>
        <link rel="stylesheet" href="/static/styles/styles.css" type="text/css" />
        <link rel="stylesheet" href="/static/css/pypi.css" type="text/css" />
        <link rel="stylesheet" href="/static/css/pypi-screen.css" type="text/css" />
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
                        <span class="breadcrumb-separator">&gt;</span>
                        <a href="/pypi/{{lastfile}}">{{infopkg.name}}</a>
                        <span class="breadcrumb-separator">&gt;</span>
                        <a href="/pypi/{{file}}">{{infopkg.version}}</a>
                    </div>
                    <div class="section">
                        <h1>{{infopkg.name}} {{infopkg.version}}</h1>
                        <div id="download-button">
                          <a class="button green" style="float:right;" href="../packages/{{file}}">Download<br>
                            <span style="font-size: 75%">{{file}}</span>
                          </a>
                        </div>
                        {{infopkg.summary}}
                        <br/>
                        <br/>
                        {{!infopkg.html}}
                        <br/>
                        <br/>
                        <ul class="nodot">
                            <li>
                                <strong>Author:</strong>
                                <span>{{infopkg.author}}</span>
                            </li>
                            <li>
                                <strong>Home Page:</strong>
                                <span>{{infopkg.home_page}}</span>
                            </li>
                            <li>
                              <strong>Categories:</strong>
                              <ul class="nodot">
                              % for cat in infopkg.classifiers:
                                <li>{{cat}}</li>
                              % end
                              </ul>
                            </li>
                            <li>
                              <strong>Platforms:</strong>
                              <ul class="nodot">
                              % for plat in infopkg.platforms:
                                <li>{{plat}}</li>
                              % end
                              </ul>
                            </li>
                            <li>
                              <strong>Other Versions:</strong>
                              <ul class="nodot">
                                  <table class="list">
                                      <tbody>
                                          <tr>
                                              <th>Updated</th>
                                              <th>File</th>
                                              <th>Size</th>
                                          </tr>
                                          % tclass = 'even'
                                          % for pkg in lstpkgs:
                                              % tclass = tclass == 'odd' and 'even' or 'odd'
                                              <tr class={{tclass}}>
                                                  <td style="white-space: nowrap; text-align: center;">{{pkg.ctime}}</td>
                                                  <td><a href="/pypi/{{pkg.relfn}}">{{pkg.relfn}}</a></td>
                                                  <td>{{pkg.size}}</td>
                                              </tr>
                                          % end
                                          <tr>
                                              <td id="last" colspan="3">
                                          </td></tr>
                                      </tbody>
                                  </table>
                              </ul>
                            </li>
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
