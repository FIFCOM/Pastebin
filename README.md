# Pastebin
Pastebin is a PHP program for storing and sharing text

Nginx Pseudo-static:

```
location / {
            rewrite ^/(J.*)$ /view.php?pb=$1 last;
        }
```
