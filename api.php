<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/fidFunctions.php");

$mode = $_REQUEST['mode'] ?? 0;
$pastebinLink = $_REQUEST['pb'] ?? 0;

if ($mode == "raw-json") pastebinRawJson($pastebinLink);

function pastebinRawJson($pb) {
    $id = pastebinGetSubString(base64_decode($pb), "$", "+");
    $key = dechex(crc32(pastebinGetSubString(base64_decode($pb), "+", "-")));
    if (pastebinView($id, $key, 'title')) {
        $raw['code'] = "1";
        $raw['id'] = "$id";
        $raw['title'] = pastebinView($id, $key, 'title') ? : "null";
        $raw['content'] = pastebinView($id, $key, 'pastebin') ? : "null";
    } else {
        $raw['code'] = "0";
        $raw['id'] = "$id";
        $raw['title'] = "null";
        $raw['content'] = "null";
    }
    header("Content-type:text/plain;charset=utf-8;");
    echo json_encode($raw, JSON_UNESCAPED_UNICODE);
}