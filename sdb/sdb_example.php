<?php
error_reporting(0);
$accessToken = 'Example_String'; //<--Please modify the Example_String to a random string of length 64
if ($_GET['accessToken'] == "" || $_GET['accessToken'] == null) {
    header("Location: https://www.fifcom.cn/error.php?reason=Empty_accessToken&from=sdb_[PRIVATE].php");
} else {
    if ($_GET['accessToken'] == "$accessToken") {
        $FileName = hash("sha512", $_GET['FileName']);
        if ($_GET['mode'] == "write") {
            if (file_exists("$FileName.txt")) {echo "exist";} else {
                $content = $_GET['PasteBin'];
                file_put_contents("$FileName.txt", "$content");
            }
        }
        if ($_GET['mode'] == "read") {
            if (file_exists("$FileName.txt")) {
                    $file = "$FileName.txt";
                    $cBody = file($file);
                    for ($i = 0; $i < count($cBody); $i++) {
                        echo $cBody[$i];
                    }
                } else {
                echo "SW52YWxpZCBQYXN0ZUJpbg==";
            }
        }
    } else {
        header("Location: https://www.fifcom.cn/error.php?reason=Error_accessToken&from=sdb_[PRIVATE].php");
    }
}
?>
