#!/usr/bin/env python

# This script generates json files from the courtfinder admin database,
# and uploads them to an S3 bucket.
# Those files are then expected to be consumed by the courtfinder search
# application

import os
import sys
import tinys3
import psycopg2
import json

try:
    S3_KEY=os.environ['S3_KEY']
    S3_SECRET=os.environ['S3_SECRET']
    S3_BUCKET=os.environ['S3_BUCKET']
    DBNAME=os.environ['COURTFINDER_DBNAME']
    DBUSER=os.environ['COURTFINDER_DBUSER']

except KeyError:
    print "You must set the following environment variables: S3_KEY, S3_SECRET, S3_BUCKET, COURTFINDER_DBUSER and COURTFINDER_DBNAME"
    sys.exit(-1)

conn = psycopg2.connect("dbname='COURTFINDER_DBNAME' user='COURTFINDER_DBUSER' host='localhost'")
exit

def courts():
    all_courts = []

    cur = conn.cursor()
    cur.execute("SELECT id, name, display, court_number, slug, latitude, longitude FROM courts")
    rows = cur.fetchall()

    for row in rows:
        admin_id, name, display, court_number, slug, lat, lon = row

        if name == None or slug == None:
#            print "- %s\n\tslug: %s, lat: %s, lon: %s" % (name, slug, lat, lon)
            continue

        aols = areas_of_law_for_court(slug)
        addresses = addresses_for_court(slug)
        court_types = court_types_for_court(slug)
        contacts = contacts_for_court(slug)
        postcodes = postcodes_for_court(slug)

        court_object = {
            "admin_id": admin_id,
            "name": name,
            "display": display,
            "court_number": court_number,
            "slug": slug,
            "areas_of_law": aols,
            "addresses": addresses,
            "court_types": court_types,
            "contacts": contacts,
            "postcodes": postcodes
        }
        if lat is not None:
            court_object['lat'] = str(lat)
        if lon is not None:
            court_object['lon'] = str(lon)
        all_courts.append(court_object)
#        print "+ %s" % name


    write_to_json( 'courts', all_courts )


def contacts_for_court( slug ):
    # contacts for court
    cur = conn.cursor()
    sql = """SELECT c.slug, ct.name as contact_type, co.telephone, co.sort
               FROM courts as c,
                    contact_types ct,
                    contacts co
              WHERE co.court_id = c.id
                AND co.contact_type_id = ct.id
                AND c.slug = '%s'""" % slug

    cur.execute(sql)
    contacts = [{
        "type": r[1],
        "number": r[2],
        "sort": r[3]
    } for r in cur.fetchall()]

    return contacts


def court_types_for_court( slug ):
    # court types for court
    cur = conn.cursor()
    sql = """SELECT ct.name as court_type
               FROM courts as c,
                    court_types ct,
                    court_types_courts ctc
              WHERE ctc.court_id = c.id
                AND ctc.court_type_id = ct.id
                AND c.slug = '%s'""" % slug

    cur.execute(sql)
    court_types =  [c[0] for c in cur.fetchall()]

    return court_types


def areas_of_law_for_court( slug ):
    # areas of law for court
    cur = conn.cursor()
    sql = """SELECT a.name
               FROM courts as c, areas_of_law as a, courts_areas_of_law as ac
              WHERE ac.court_id = c.id
                AND ac.area_of_law_id = a.id
                AND c.slug = '%s'""" % slug

    cur.execute(sql)
    aol_list = [a[0] for a in cur.fetchall()]

    aols = []
    for aol_name in aol_list:
        cur = conn.cursor()
        sql = """SELECT co.name
                   FROM court_council_links as ccl,
                        areas_of_law as aol,
                        courts as c,
                        councils as co
                  WHERE ccl.court_id = c.id
                    AND ccl.area_of_law_id = aol.id
                    AND ccl.council_id = co.id
                    AND c.slug = '%s'
                    AND aol.name = '%s'""" % (slug, aol_name)

        cur.execute(sql)
        councils = [c[0] for c in cur.fetchall()]

        aols.append({
            "name": aol_name,
            "councils": councils
        })

    return aols


def postcodes_for_court( slug ):
    cur = conn.cursor()
    sql = """SELECT pc.postcode
               FROM postcode_courts pc,
                    courts c
              WHERE pc.court_id = c.id
                AND c.slug = '%s'""" % slug

    cur.execute(sql)
    postcodes = [p[0] for p in cur.fetchall()]

    return postcodes

def addresses_for_court( slug ):
    # addresses for court
    cur = conn.cursor()
    sql = """SELECT t.name as town,
                    at.name as address_type,
                    a.address_line_1,
                    a.address_line_2,
                    a.address_line_3,
                    a.address_line_4,
                    a.postcode
               FROM courts as c,
                    address_types as at,
                    addresses as a,
                    towns as t
              WHERE a.court_id = c.id
                AND a.address_type_id = at.id
                AND a.town_id = t.id
                AND c.slug = '%s'""" % slug

    cur.execute(sql)
    addresses = [{
        "type": row[1],
        "address" : "\n".join([row[2], row[3], row[4], row[5]]),
        "postcode": row[6],
        "town": row[0],
    } for row in cur.fetchall()]
    return addresses



#def areas_of_law():
#    cur = conn.cursor()
#    cur.execute("SELECT name, slug FROM areas_of_law")
#    rows = cur.fetchall()
#
#    all_aols = [{"name": name, "slug": slug } for name, slug in rows]
#    write_to_json( 'areas_of_law', all_aols )
#
#
#def court_types():
#    cur = conn.cursor()
#    cur.execute("SELECT name, slug FROM court_types")
#    rows = cur.fetchall()
#
#    all_court_types = [{"name": name, "slug": slug } for name, slug in rows]
#    write_to_json( 'court_types', all_court_types )


def town_county_country():
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM countries")

    countries = []
    country_names = cur.fetchall()

    for country_id, country_name in country_names:
        cur.execute("""SELECT co.id, co.name
                         FROM countries as c,
                              counties as co
                        WHERE co.country_id = c.id
                          AND c.id = %s""" % country_id )

        counties = []
        county_names = cur.fetchall()
        for county_id, county_name in county_names:
            cur.execute("""SELECT t.name
                             FROM counties as c,
                                  towns as t
                            WHERE t.county_id = c.id
                              AND c.id = %s""" % county_id)

            towns = [r[0] for r in cur.fetchall()]
            counties.append({
                "name": county_name,
                "towns": towns
            })

        countries.append({
            "name": country_name,
            "counties": counties
        })

    write_to_json("countries", countries)


def write_to_json( filename, obj ):
    with open('/tmp/%s.json' % filename, 'w') as outfile:
        json.dump(obj, outfile, indent=4, separators=(',', ': '))
#        print "== /tmp/%s.json written" % filename
        outfile.close()

def upload_to_s3():
    print('uploading json files to S3...'),
    conn = tinys3.Connection(S3_KEY,
                             S3_SECRET,
                             tls=True,
                             endpoint='s3-eu-west-1.amazonaws.com')
    f = open('/tmp/courts.json', 'rb')
    conn.upload('courts.json', f, S3_BUCKET)
    f = open('/tmp/countries.json', 'rb')
    conn.upload('countries.json', f, S3_BUCKET)
    print 'uploaded'


if __name__ == '__main__':
    print('generating json files...'),
    courts()
    town_county_country()
    print 'done'
    upload_to_s3()
