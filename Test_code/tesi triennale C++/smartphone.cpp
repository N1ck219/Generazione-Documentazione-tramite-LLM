#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <cmath>
#include "smartphone.hpp"
// #include "istruzioni.hpp"

#define OCC 1
#define LIB 0

using namespace std;

griglia::griglia(string nome_file)
{
    int x, y, temp1, temp2 = 0;

    vector<int> temp;
    lavoro task_temp;

    ifstream is(nome_file);

    if (!is.is_open())
    {
        cout << "Errore apertura file" << endl;
        exit(1);
    }

    is >> w >> h >> r >> m >> t >> l; // dimensioni

    for (int i = 0; i < m; i++) // coordinate mounting point
    {
        is >> temp1;
        is >> temp2;
        mount_point.push_back(make_pair(temp1, temp2));
    }

    while (is >> x >> y)
    {
        task_temp.svuota();

        task_temp.InserisciPrimi(x, y); // mette i primi due valori della task
        for (int j = 0; j < task_temp.num_ass_point; j++)
        {
            is >> x >> y;
            task_temp.InserisciCoord(x, y); // mette tutte le coordinate
        }

        task.push_back(task_temp);
    }

    vector<int> vet_temp_h(h);
    // vector<int> vet_temp_w(w);

    for (int i = 0; i < w; i++)
    {
        valori_griglia.push_back(vet_temp_h);
    }

    for (int i = 0; i < m; i++)
    {

        for (int j = 0; j < w; j++)
        {

            for (int k = 0; k < h; k++)
            {

                if (j == mount_point[i].first && k == mount_point[i].second)
                {
                    valori_griglia[j][k] = OCC;
                }
                else
                {
                    if (valori_griglia[j][k] != OCC)
                        valori_griglia[j][k] = LIB;
                }
            }
        }
    }
}

ostream &operator<<(ostream &os, const griglia &g)
{
    os << "Dimensioni: " << g.w << "x" << g.h << endl;
    os << "Numero bracci: " << g.r << endl;
    os << "Numero mounting point: " << g.m << endl;
    os << "Numero task: " << g.t << endl;
    os << "Numero step: " << g.l << endl;

    // Stampa tutte info
    for (int i = 0; i < g.m; i++)
    {
        os << i + 1 << ")Mount point in [" << g.mount_point[i].first << ", " << g.mount_point[i].second << "]" << endl;
    }

    for (int i = 0; i < g.t; i++)
    {
        os << "La task " << i << " " << g.task[i] << endl;
    }

    // Stampa tabella
    // for (int j = g.h - 1; j >= 0; j--)
    // {
    //     for (int i = 0; i < g.w; i++)
    //     {
    //         // cout << "w: " << i << " h: " << j << " " << g.valori_griglia[i][j] << endl;
    //         cout << g.valori_griglia[i][j];
    //     }
    //     cout << endl;
    // }

    return os;
}

void lavoro::InserisciPrimi(int x, int y)
{
    punteggio = x;
    num_ass_point = y;
}

void lavoro::InserisciCoord(int x, int y)
{
    pos.push_back(make_pair(x, y));
}

lavoro &lavoro::operator=(const lavoro &l)
{

    this->punteggio = l.punteggio;
    this->num_ass_point = l.num_ass_point;
    this->pos = l.pos;

    return *this;
}

ostream &operator<<(ostream &os, const lavoro &l)
{
    cout << "vale " << l.punteggio << " punti con " << l.num_ass_point << " punti di assemblaggio. ";

    for (int i = 0; i < l.num_ass_point; i++)
    {
        cout << "[" << l.pos[i].first << ", " << l.pos[i].second << "]";
    }

    return os;
}
