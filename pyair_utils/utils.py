#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
**Various functions

"""

import copy
import pandas as pd


def pivot_csv(fin, fout, nb_cols=1, nb_rows=1, sep=","):
    """Renvoie une table de pivot où les valeurs stockées en colonnes dans un
    fichier CSV seront retournées en ligne.
    Prérequis :
        - la première ligne contient les en-têtes de colonne
        - les nb_cols premières colonnes contiennent une référence d'enregistrement

    Exemple :
        en entrée :
            Source_name,CO,NO2,NOX
            ROUTE_1,0.0020091357,0.0003510306,0.0012975298
        retournera en sortie :
            ROUTE_1,CO,0.0020091357
            ROUTE_1,NO2,0.0003510306
            ROUTE_1,NOX,0.0012975298

    Paramètres:
        fin : nom du fichier d'entrée où sont stockées les données
        fout: nom du fichier où enregistrer le résultat
        nb_cols: nombre de colonne à utiliser comme référence (par défaut 1)
        nb_rows: nombre de lignes d'en-tête (par défaut 1)
        sep : séparateur de colonne

    """

    f = open(fin, "rb")
    lines = f.readlines()
    f.close()
    head = [head.strip().split(sep)[nb_cols:] for head in lines[0:nb_rows]]
    head = pd.DataFrame(head).T.to_records(index=False)

    f = open(fout, "wb")

    for nline, line in enumerate(lines[nb_rows:]):
        vals = line.strip().split(sep)
        refs = vals[0:nb_cols]
        datas = vals[nb_cols:]
        try:
            for i, v in enumerate(datas):
                l = copy.deepcopy(refs)
                l.extend(head[i])
                l.append(v)
                f.write("%s\n" %sep.join(l))
        except Exception, err:
            print("Erreur sur la ligne %i: %s"%(nline, err))
    f.close()


def dissolve_mask(a, b):
    """Dissout les masques des 2 series de données passées en paramètres.

    Paramètres:
    a & b: (pandas.Series)

    Retourne:
    a et b modifiés tel que toute valeur nulle (nan) dans la série a soit aussi
    mise à nulle (nan) dans la série b, et inversement
    """
    mask = a.isnull() | b.isnull()
    a = a.mask(mask)
    b = b.mask(mask)
    return a, b


def dissolveMask(a, b):
    return dissolve_mask(a, b)


def df_from_MF(fname, sep=';', decimal=',', date_format='%Y%m%d%H'):
    """Créait un DataFrame temporel depuis un fichier CSV Météo-France

    Paramètres:
    fname: nom du fichier CSV Météo-France à lire
    sep: Séparateur de colonne
    decimal: Séparateur décimal
    date_format: Descripteur de format de la colonne date

    Retourne:
    Un DataFrame temporel
    """

    df = pd.read_csv(fname, sep=sep, decimal=decimal, parse_dates=['DATE'],
                     date_parser=lambda x: pd.to_datetime(x, format=date_format)
                     )
    df = df.set_index('DATE')
    return df

