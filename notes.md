# Notes

> [cookies reference](https://www.mycourseville.com/cookiepolicy.html)

curl '<https://www.mycourseville.com/?q=courseville/ajax/cvhomepanel_get_filter>' -b 'SESS...' \

cv-assignment-table\
courseville-assignment-list -> THE THING BEING FADED IN\

courseville-assignment-subpage-loading

style="opacity: 0.585965;"

THE ASSIGNMENTS SHOW UP INSTANTLY. THE LOADING AND FADING IS ALL FAKE. THATS WHY I COULDNT FIND IT IN THE XHR REQUESTS. ITS BEEN IN THE DOC SINCE THE BEGINNING, IT WAS JUST DISPLAY:NONE, I LOVE MCV

## Load more assignments request

curl '<https://www.mycourseville.com/?q=courseville/ajax/loadmoreassignmentrows>' \
-b 'SESS...' \
--data-raw 'cv_cid=...&next=5'

### Sample response

{
"status": 1,
"data": {
"html": "..."
},
"next": 10,
"loadmoremsg": "Showing 10 items from 24 published items."
}

## Login

### OAuth request

curl '<https://www.mycourseville.com/api/oauth/authorize?response_type=code&client_id=mycourseville.com&redirect_uri=https://www.mycourseville.com>'

### Login request

curl '<https://www.mycourseville.com/api/chulalogin>' \
-b 'SESS...' \
--data-raw '_token=...&username=asd&password=12345&remember=on'

## This disappears when all assignments are loaded

courseville-assignment-list-loadmore-panel

## This unhides after its all loaded. If there were <= 5 assignments since the start, only this is here. Yes this one always exists

courseville-assignment-list-all-shown-notice

## TODO

### DONE

spam load more until no more left
'data-next' attribute is used to tell the server the current number of assingments
so it should be 5 -> 10 -> 15 -> until the max which is findable in courseville-assignment-list-loadmore-panel

save login cookies to a file to reuse
