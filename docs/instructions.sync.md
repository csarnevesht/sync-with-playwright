List of account folder names in accounts/main.txt

Write a sync tool sync/sync_analyze that does the following:
using logic from:
 dropbox analyzer (see dropbox/cmd_analyze.py)
 salesforce account fuzzy search (see salesforce/cmd_fuzzy.py)

for each dropbox account fol
der:
    uses fuzzy search in salesforce, 
      if it has an exact match:
        navigates to the salesforce account and gets the list of all the salesforce account files
        gets the list of account dropbox files, this list should also contain modified date information.
        for each account dropbox file:
            set original_dropbox_filename
            set renamed_dropbox_filename to original_dropbox_filename prefixed with the modified date using format YYMMDD{original_dropbox_filename} if original_dropbox_filename is not already prefixed as 'YYMMDD<filename>' or 'YYMMDD <filename>'
            it searches for renamed_dropbox_filename in the list of salesforce account files
               if it finds it save it in a list
               if it doesn't find it
                   set renamed_dropbox_filename to original_dropbox_filename prefixed with the modified date using format 'YYMMDD {original_dropbox_filename}' if original_dropbox_filename is not already prefixed as 'YYMMDD<filename>' or 'YYMMDD <filename>'
                   search again
               if it does not find it at all save it in a list

      if no exact match for account, print match information

      report all information for each account and account files 

        


