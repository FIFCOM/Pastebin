<?php
require_once("config/pastebinConfig.php");
require_once("pages/pastebinFunctions.php");
require_once("pages/fidFunctions.php");

$mode = $_REQUEST['mode'] ?? 0;
$pastebinLink = $_REQUEST['pb'] ?? 0;

if ($mode == "raw" && $pastebinLink) pastebinRawJson($pastebinLink);

function pastebinRawJson($pb) {
    $id = pastebinGetSubString(base64_decode($pb), "$", "+");
    $key = dechex(crc32(pastebinGetSubString(base64_decode($pb), "+", "-")));
    if (pastebinView($id, $key, 'title')) {
        $json['code'] = "1";
        $json['id'] = "$id";
        $json['title'] = pastebinView($id, $key, 'title') ? : "null";
        $json['content'] = pastebinView($id, $key, 'pastebin') ? : "null";
    } else {
        $json['code'] = "0";
        $json['id'] = "$id";
        $json['title'] = "null";
        $json['content'] = "null";
    }
    header("Content-type:text/plain;charset=utf-8;");
    echo json_encode($json, JSON_UNESCAPED_UNICODE);
}