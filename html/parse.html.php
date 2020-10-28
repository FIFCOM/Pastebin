<!DOCTYPE html>
<html>
<head>
    <title>PasteBin - FIFCOM</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="keywords" content="PasteBin service developed by FIFCOM" />
    <script type="application/x-javascript"> addEventListener("load", function() { setTimeout(hideURLbar, 0); }, false); function hideURLbar(){ window.scrollTo(0,1); } </script>
    <link href="css/style.css" rel="stylesheet" type="text/css" media="all" />
</head>
<body>
<SCRIPT LANGUAGE="JavaScript"> 
 function copyinput() 
 { 
 var input=document.getElementById("pastebin");
 input.select();
 document.execCommand("Copy");
 } 
 </SCRIPT>
<div class="main main-agileinfo">
    <h1>FIFCOM PasteBin</h1>
    <div class="main-agilerow">
        <div class="sub-w3lsright agileits-w3layouts stack twisted">
            <h2>FIFCOM PasteBin</h2>
            <p><span><a href="https://<?=$SvrName?>/<?=$pbName?>&raw=true" target="_blank">RAW</a></span> | <span><a href="https://<?=$SvrName?>" target="_blank">Create a new PasteBin</a></span></p>
            <form action="#" method="post">
                <textarea class="form-control" name="pastebin" id="pastebin" rows="1" onclick=copyinput() placeholder=" Nothing to show."><?=$pastebin?></textarea>
                <input type="button" value="Copy to clipboard" onclick="copyinput()"/>
            </form>
            <div class="clear"> </div>
        </div>
        <div class="clear"> </div>
    </div>
</div>
<div class="copyw3-agile">
    <p> © 2020 Fifcom Technology Studio | <a href="https://github.com/FIFCOM/Pastebin" target="_blank">PasteBin <?=PASTEBIN_VERSION?></a></p>
</div>
</body>
</html>
