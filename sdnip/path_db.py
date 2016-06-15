'''
DB for sroting path

Structure of db:
{
    'ip prefix 1': {
        'dpid 1': 'output port',
        ...
    },
    ....
}
'''

class PathDB(dict):

    def __init__(self):
        super(PathDB, self).__init__()
