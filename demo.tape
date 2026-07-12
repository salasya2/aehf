# vhs tape for the aehf demo GIF.
# Run with:  vhs demo.tape    (reliable in WSL/Linux; flaky on native Windows —
# use ScreenToGif there instead). Both commands run offline: mock tools +
# assertion judge, so no API wait and no API key needed.

Output docs/demo.gif

Set FontSize 18
Set Width 1200
Set Height 600
Set Padding 20

Type "aehf run examples/calibration_suite.yaml anthropic mock --judgechoice assertion"
Enter
Sleep 5s

Type "aehf calibrate labels/labels_filled.jsonl assertion"
Enter
Sleep 5s
