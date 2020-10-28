# Pastebin
Pastebin is a simple PHP program for storing and sharing text

Nginx Pseudo-static:

```
location / {
            rewrite ^/(.+)$ /parse.php?pb=$1 last;
        }
```
