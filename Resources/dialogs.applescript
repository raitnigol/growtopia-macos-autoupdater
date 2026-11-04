on run argv
    set dialogKind to item 1 of argv
    set dialogText to my expandNewlines(item 2 of argv)
    if dialogKind is "setup" then
        set answer to display dialog dialogText with title "Growtopia Launcher" buttons {"Cancel", "Keep macOS Checks", "Trust Official Downloads"} default button "Keep macOS Checks" cancel button "Cancel" with icon caution
    else if dialogKind is "offline" then
        set answer to display dialog dialogText with title "Growtopia Launcher" buttons {"Cancel", "Launch Installed"} default button "Launch Installed" cancel button "Cancel" with icon caution
    else if dialogKind is "unsigned" then
        set answer to display dialog dialogText with title "Growtopia Launcher" buttons {"Cancel", "Install This Build"} default button "Cancel" cancel button "Cancel" with icon caution
    else if dialogKind is "running" then
        set answer to display dialog dialogText with title "Growtopia Launcher" buttons {"Cancel", "Open Running Game"} default button "Open Running Game" cancel button "Cancel"
    else if dialogKind is "settings" then
        set answer to display dialog dialogText with title "Growtopia Launcher Settings" buttons {"Close", "Download Source", "More"} default button "Close"
    else if dialogKind is "source" then
        set answer to display dialog dialogText with title "Download Source" buttons {"Cancel", "Website Beta", "In-Game CDN"} default button "In-Game CDN" cancel button "Cancel"
    else if dialogKind is "more" then
        set choices to {"Force Fresh Download", "Change Trust Setting", "Restore Previous Version", "Open Log", "Open Game Folder", "Use Personal Applications Folder"}
        set answer to choose from list choices with title "Growtopia Launcher Settings" with prompt dialogText
        if answer is false then return "Cancel"
        return item 1 of answer
    else if dialogKind is "restore" then
        set answer to display dialog dialogText with title "Restore Growtopia" buttons {"Cancel", "Restore"} default button "Cancel" cancel button "Cancel" with icon caution
    else
        error "Unknown dialog type"
    end if
    return button returned of answer
end run

on expandNewlines(inputText)
    set previousDelimiters to AppleScript's text item delimiters
    set AppleScript's text item delimiters to "\\n"
    set textParts to text items of inputText
    set AppleScript's text item delimiters to linefeed
    set expandedText to textParts as text
    set AppleScript's text item delimiters to previousDelimiters
    return expandedText
end expandNewlines
