import shutil
import time
warning = \
'''

##########################################################################
# This program will RESET the database.db to a known working database.db #
##########################################################################

Press ENTER to proceed

'''
input(warning)
try:
    shutil.move('database.db', f'backup/old/database.db.{time.time_ns()}.old')
except Exception as e:
    print(f'Exception Occured: {str(e)}')
try:
    shutil.copy('backup/working/database.db','database.db')
except Exception as e:
    print(f'Exception Occured: {str(e)}')
