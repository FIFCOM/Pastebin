<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/fidFunctions.php");

function pastebinRaw($id, $key, $type) {
    if ($id && $key) {
        $raw = pastebinView($id, $key, $type);
        header("Content-type:text/plain;charset=utf-8;");
        echo $raw ? "null" : $raw;
    } else {
        header("Content-type:text/plain;charset=utf-8;");
        echo "param error.";
    }
}