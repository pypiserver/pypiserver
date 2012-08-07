    <h1>Welcome to pypiserver!</h1>

    <p>This is a PyPI compatible package index serving {{NUMPKGS}} packages.</p>

    <p> To use this server with pip, run the the following command:
    <blockquote><pre>
    pip install -i {{URL}}simple/ PACKAGE [PACKAGE2...]
    </pre></blockquote></p>

    <p> To use this server with easy_install, run the the following command:
    <blockquote><pre>
    easy_install -i {{URL}}simple/ PACKAGE
    </pre></blockquote></p>

    <p>The complete list of all packages can be found <a href="packages/">here</a> or via the <a href="simple/">simple</a> index.</p>

    <p>This instance is running version {{VERSION}} of the <a href="http://pypi.python.org/pypi/pypiserver">pypiserver</a> software.</p>
%rebase layout
