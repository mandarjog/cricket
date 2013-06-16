from crincinfo_import import import_playerresults

teams = [ 'india', 'pakistan', 'australia','england', 
            'west indies', 'south africa','sri lanka',
            'new zealand']
def main():
    import sys
    if len(sys.argv) < 4:
        print sys.argv[0], "filename country playername"
        sys.exit(2)

    team = sys.argv[2]
    if team not in teams:
        print team, "should be in", teams
        sys.exit(2)

    data=open(sys.argv[1], 'rt').read()
    import_playerresults(data, sys.argv[2], sys.argv[3])

if __name__ == "__main__":
    main()
