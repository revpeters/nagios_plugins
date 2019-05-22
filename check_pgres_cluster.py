#!/usr/bin/python3.6

import argparse
import subprocess
import sys

parser = argparse.ArgumentParser(description='Check Status of HA Cluster')
parser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')
parser.add_argument('--hostname', '-H', help='Host name of the PGPool Master', required=True)

args = parser.parse_args()

pgpool_hosts = []
pgpool_master = []
pgpool_standby = []

pgres_hosts = []
pgres_prime = []
pgres_standby = []

pgres_cluster = []
pgpool_cluster = []
cluster = [[0,0,0],[0,0,0]]

ssh_options = f'-q -i /var/adm/rational/clearcase/.ssh/id_rsa.postgres.prod.on-premises'

pgpool_cmd = f'ssh {ssh_options} postgres@{args.hostname} \'pcp_watchdog_info -w\' | grep 9000'
postgres_cmd = f'psql -U postgres -h {args.hostname} -p 5432 -c \'show pool_nodes;\' | grep 5493'

pool_out = subprocess.run(pgpool_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, encoding='utf-8')
pgres_out = subprocess.run(postgres_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, encoding='utf-8')

pgpool = pool_out.stdout.splitlines()
postgres = pgres_out.stdout.splitlines()

'''
pgpool - master | standby | standby

         hostname             role
         pgpool_hosts[i][3] | pgpool_hosts[i][7]

pgres  - primary(up)       | standby(up)        | standby(up)

         hostname            role                 status
         pgres_hosts[i][2] | pgres_hosts[i][10] | pgres_hosts[i][6]
'''

# Postgres
for i in range(len(postgres)):
    pgres_hosts.append(postgres[i].split())

for i in range(len(pgres_hosts)):
    pgres_cluster.append([pgres_hosts[i][10], pgres_hosts[i][6]])


# PGPOOL
for i in range(len(pgpool)):
    pgpool_hosts.append(pgpool[i].split())

for i in range(len(pgpool_hosts)):
    pgpool_cluster.extend([pgpool_hosts[i][7]])


def cluster_status():

    # Look for bad pgpool nodes
    for node in pgpool_cluster:
        if node == 'MASTER':
            if cluster[0][0] == 1:
                print("PGPool Cluster CRITICAL: More than one Master node found")
                sys.exit(2)
            else:
                cluster[0][0] = 1
        elif node == 'STANDBY':
            if cluster[0][1] == 1:
                cluster[0][2] = 1
            else:
                cluster[0][1] = 1

    # Look for bad postgres nodes
    for node in pgres_cluster:
        if node == ['primary', 'up']:
            if cluster[1][0] == 1:
                print("PGPool Cluster CRITICAL: More than one Primary node found")
                sys.exit(2)
            else:
                cluster[1][0] = 1
        elif node == ['standby', 'up']:
            if cluster[1][1] == 1:
                cluster[1][2] = 1
            else:
                cluster[1][1] = 1


    # Is the cluster down?
    if cluster[0][0] + cluster[1][0] == 0:
        print("PGPool Cluster CRITICAL: Cluster down")
        sys.exit(2)
    # Is the Master or Primary down?
    elif cluster[0][0] + cluster[1][0] == 1:
        if cluster[0][0]:
            print("Postgres Cluster CRITICAL: Postgres Master down")
            sys.exit(2)
        else:
            print("PGPool Cluster CRITICAL: PGPool Primary down")
            sys.exit(2)
    # Is the cluster no longer HA?
    elif cluster[0][1] + cluster[1][1] == 0:
        print("PGPool Cluster WARNING: Cluster is no longer HA")
        sys.exit(1)
    # Is PGPool or Postgres no longer HA?
    elif cluster[0][1] + cluster[1][1] == 1:
        if cluster[0][1]:
            print("Postgres Cluster WARNING: Postgres no longer HA")
            sys.exit(1)
        else:
            print("PGPool Cluster WARNING: PGPool no longer HA")
            sys.exit(1)
    # Does the cluster have a node down?
    elif cluster[0][2] + cluster[1][2] == 0:
        print("PGPool Cluster WARNING: PGPool and Postgres Standby down")
        sys.exit(1)
    # Is a PGPool or Postgres node down?
    elif cluster[0][2] + cluster[1][2] == 1:
        if cluster[0][2]:
            print("Postgres Cluster WARNING: Postgres node is down")
            sys.exit(1)
        else:
            print("PGPool Cluster WARNING: PGPool node is down")
            sys.exit(1)
    else:
        print("PGPool Cluster OK: Cluster is healthy")
        sys.exit(0)


cluster_status()
print(" ")
