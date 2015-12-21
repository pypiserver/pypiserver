
<html>
    <head>
        <title>Links for {{prefix}}</title>
    </head>
    <body>
        <h1>Links for {{prefix}}</h1>
        % for file, href in links:
             <a href="{{href}}">{{file}}</a><br>
    </body>
</html>
