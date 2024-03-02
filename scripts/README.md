## Scripts

[`update_image_links`](https://github.com/Cockatrice/Magic-Token/blob/master/scripts/update_image_links.py)  
This script changes the links from the old CDN on c1.scryfall.com to the new CDN on cards.scryfall.io.  
It reads a tokens.xml file containing CDN picURLs of either version, makes requests to the Scryfall API
to receive the most up-to-date URLs for each token, and generates an output file.  
`--inplace / -i` will update the input file  
`--output / -o` will create a new file of your choice

Basic call to run the script:
```
python3 update_image_links.py tokens.xml -i
```
