#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <cmath>
#include <algorithm>
#include "smartphone.hpp"
#include "istruzioni.hpp"

#define OCC 1
#define LIB 0
#define R 1
#define L 2
#define U 3
#define D 4

using namespace std;

ostream &operator<<(ostream &os, const istruzioni &ist)
{
    cout << "Punteggio realizzato: " << ist.GetPuntTot() << endl;
    cout << "Task completate: " << ist.GetNumTaskCompl() << endl;

    return os;
}

ostream &operator<<(ostream &os, const vector<vector<int>> &valori_g)
{

    int prova = 4 - 1;

    for (int j = prova; j >= 0; j--)
    {
        os << j;
        for (int i = 0; i < 5; i++)
        {
            // cout << "w: " << i << " h: " << j << " " << g.valori_griglia[i][j] << endl;
            cout << " " << valori_g[i][j] << " ";
        }
        os << endl;
    }
    os << "  0  1  2  3  4" << endl;

    return os;
}

istruzioni::istruzioni(const griglia &g)
{
    ofstream output("test.txt");
    output << "Prova" << endl;

    n_braccia_utilizzate = g.getR();
    // n_braccia_utilizzate = 3;
    mount_point = g.getMount_point();
    num_task = g.getT();
    w = g.getW();
    // cout << g.getW() << endl;
    h = g.getH();
    num_step = g.getL();
    punteggio_totale = 0;
    num_task_compl = 0;

    vector<vector<int>> task_per_quadrante(n_braccia_utilizzate);
    vector<vector<int>> task_per_quadrante_ordinate(n_braccia_utilizzate);

    for (int i = 0; i < num_task; i++)
    {
        task_i.push_back(g.getLavoro(i));
    }

    vector<vector<int>> valori_g = g.getValori();

    // for (int j = (g.h - 1); j >= 0; j--)
    // {

    //     for (int i = 0; i < g.w; i++)
    //     {
    //         // cout << "w: " << i << " h: " << j << " " << g.valori_griglia[i][j] << endl;
    //         cout << g.valori_griglia[i][j];
    //     }
    //     cout << " " << j;
    //     cout << endl;
    // }

    SuddivisioneGriglia(&task_per_quadrante);

    AccoppiaMPQuadrante();

    // cout << "PRIMA" << endl;
    // for (int i = 0; i < n_braccia_utilizzate; i++)
    // {

    //     cout << "   Task in quadrante " << i << ": ";

    //     for (unsigned j = 0; j < task_per_quadrante[i].size(); j++)
    //     {
    //         cout << task_per_quadrante[i][j] << " ";
    //     }
    //     cout << endl;
    // }

    int metodo;
    cout << "Scegli metodo da usare (0 -> nessuno ordinamento, 1 -> ordinamento per punteggio, 2 -> ordinamento per lunghezza): ";
    cin >> metodo;

    if (metodo == 0)
    {
        task_per_quadrante_ordinate = task_per_quadrante; // lascio tutto come è
    }
    else if (metodo == 1)
    {
        task_per_quadrante_ordinate = OrdinaTaskPerPunteggioPerQuadrante(&task_per_quadrante);
    }
    else if (metodo == 2)
    {
        task_per_quadrante_ordinate = OrdinaTaskPerLunghezzaPerQuadrante(&task_per_quadrante);
    }
    else
    {
        cerr << "Metodo non esistente" << endl;
        exit(1);
    }

    // cout << "DOPO" << endl;
    // for (int i = 0; i < n_braccia_utilizzate; i++)
    // {

    //     cout << "   Task in quadrante " << i << ": ";

    //     for (unsigned j = 0; j < task_per_quadrante_ordinate[i].size(); j++)
    //     {
    //         cout << task_per_quadrante_ordinate[i][j] << " ";
    //     }
    //     cout << endl;
    // }

    Instradamento(num_step, valori_g, &task_per_quadrante_ordinate, output);

    output.close();
}

void istruzioni::SuddivisioneGriglia(vector<vector<int>> *task_per_quadrante)
{

    if (n_braccia_utilizzate == 1)
    {
        for (int i = 0; i < num_task; i++)
        {
            (*task_per_quadrante)[0].push_back(i);
        }
    }
    else if (n_braccia_utilizzate == 2)
    {
        // cout << "ok2" << endl;
        double meta = w / 2.0;
        // cout << "meta di " << w << " -> " << meta << endl;

        for (int i = 0; i < num_task; i++)
        {
            if (task_i[i].pos[0].first <= meta)
            {
                // cout << task_i[i].pos[0].first << " < " << meta << " --> ";
                (*task_per_quadrante)[0].push_back(i);
                // cout << "sx" << endl;
            }
            else
            {
                // cout << task_i[i].pos[0].first << " > " << meta << " --> ";
                (*task_per_quadrante)[1].push_back(i);
                // cout << "dx" << endl;
            }
        }
    }
    else if (n_braccia_utilizzate > 2 && n_braccia_utilizzate % 2 == 0)
    {
        double metah = h / 2.0;
        double dim_colonne = w / (n_braccia_utilizzate / 2);
        int num_colonne = n_braccia_utilizzate / 2;
        int indice = 0;
        // cout << "metah: " << metah << ", dim_colonne: " << dim_colonne << endl;
        for (int i = 0; i < num_task; i++)
        {
            // cout << i << "----------------" << endl;
            if (task_i[i].pos[0].first == 0)
            {
                indice = 0;
            }
            else
            {
                indice = ceil((task_i[i].pos[0].first / dim_colonne)) - 1; //-1 perche parto da 0
                // cout << indice << " = (" << task_i[i].pos[0].first << " / " << dim_colonne << ") -1" << endl;
            }

            if (task_i[i].pos[0].second >= metah)
            {
                // cout << task_i[i].pos[0].second << " > " << metah << endl;
                // cout << "indice: " << indice << endl;
                (*task_per_quadrante)[indice].push_back(i);
                // cout << "sopra" << endl;
            }
            else
            {
                // cout << task_i[i].pos[0].second << " < " << metah << endl;
                indice = indice + num_colonne;
                // cout << "indice: " << indice << endl;
                (*task_per_quadrante)[indice].push_back(i);
                // cout << "sotto" << endl;
            }
            // cout << endl;
        }
        // cout << "pari" << endl;
    }
    else if (n_braccia_utilizzate > 2 && n_braccia_utilizzate % 2 == 1)
    {
        double metah = h / 2.0;
        double dim_colonne = w / ((n_braccia_utilizzate + 1) / 2);
        int num_colonne = (n_braccia_utilizzate + 1) / 2;
        int indice = 0;
        // cout << "metah: " << metah << ", colonne: " << colonne << endl;
        for (int i = 0; i < num_task; i++)
        {
            if (task_i[i].pos[0].first == 0)
            {
                indice = 0;
            }
            else
            {
                indice = ceil((task_i[i].pos[0].first / dim_colonne)) - 1; //-1 perche parto da 0
            }

            // cout << "i: " << i << "     indice: " << indice << endl;

            if (task_i[i].pos[0].second >= metah)
            {
                // cout << task_i[i].pos[0].second << " > " << metah << endl;
                // cout << "indice: " << indice << endl;
                (*task_per_quadrante)[indice].push_back(i);
                // cout << "sopra" << endl;
            }
            else
            {
                // cout << task_i[i].pos[0].second << " < " << metah << endl;
                indice = indice + num_colonne;
                if (indice == n_braccia_utilizzate)
                {
                    indice--;
                }

                // cout << "indice: " << indice << endl;
                (*task_per_quadrante)[indice].push_back(i);
                // cout << "sotto" << endl;
            }
            // cout << endl;
        }
        // cout << "dispari" << endl;
    }
}

void istruzioni::AccoppiaMPQuadrante()
{
    double metaw = w / 2.0;
    double metah = h / 2.0;
    // w = 11;
    // double colonne = ((n_braccia_utilizzate + 1) / 2);
    // cout << "colonne = " << n_braccia_utilizzate + 1 << " / 2" << endl;
    // cout << "colonne: " << colonne << endl;
    int indice = 0;
    CoppiaMPQuadrante.resize(n_braccia_utilizzate);
    vector<int> quadrante_raggiunto(n_braccia_utilizzate, 0);
    vector<int> mp_assegnati;

    if (n_braccia_utilizzate == 1)
    {
        CoppiaMPQuadrante[0] = 0;
        cout << "quad unico" << endl;
    }
    else if (n_braccia_utilizzate == 2)
    {
        for (unsigned i = 0; i < mount_point.size(); i++)
        {
            if (mount_point[i].first <= metaw && quadrante_raggiunto[0] == 0)
            {
                CoppiaMPQuadrante[0] = i;
                cout << "quad: 0  -> mp: " << i << endl;
                quadrante_raggiunto[0] = 1;
                mp_assegnati.push_back(i);
            }
            else if (mount_point[i].first > metaw && quadrante_raggiunto[1] == 0)
            {
                CoppiaMPQuadrante[1] = i;
                cout << "quad: 1  -> mp: " << i << endl;
                quadrante_raggiunto[1] = 1;
                mp_assegnati.push_back(i);
            }
        }
    }
    else if (n_braccia_utilizzate > 2 && n_braccia_utilizzate % 2 == 0)
    {
        // cout << "metah: " << metah << endl;

        for (unsigned i = 0; i < mount_point.size(); i++)
        {
            double dim_colonne = w / ((n_braccia_utilizzate) / 2);
            int num_colonne = (n_braccia_utilizzate) / 2;
            if (mount_point[i].first == 0)
            {
                indice = 0;
            }
            else
            {
                indice = ceil((mount_point[i].first / dim_colonne)) - 1; //-1 perche parto da 0
            }

            if (mount_point[i].second >= metah && quadrante_raggiunto[indice] == 0)
            {
                cout << "quad: " << indice << " -> mp: " << i << endl;
                CoppiaMPQuadrante[indice] = i;
                quadrante_raggiunto[indice] = 1;
                mp_assegnati.push_back(i);
            }
            else if (quadrante_raggiunto[indice] == 0)
            {
                indice = indice + num_colonne;
                if (indice == n_braccia_utilizzate)
                {
                    indice--;
                }
                cout << "quad: " << indice << " -> mp: " << i << endl;
                CoppiaMPQuadrante[indice] = i;
                quadrante_raggiunto[indice] = 1;
                mp_assegnati.push_back(i);
            }
        }
    }
    else if (n_braccia_utilizzate > 2 && n_braccia_utilizzate % 2 == 1)
    {
        // cout << "metah: " << metah << endl;
        double dim_colonne = w / ((n_braccia_utilizzate + 1) / 2);
        int num_colonne = (n_braccia_utilizzate + 1) / 2;

        for (unsigned i = 0; i < mount_point.size(); i++)
        {
            if (mount_point[i].first == 0)
            {
                indice = 0;
            }
            else
            {
                indice = ceil((mount_point[i].first / dim_colonne)) - 1; //-1 perche parto da 0
            }

            if (mount_point[i].second >= metah && quadrante_raggiunto[indice] == 0)
            {
                cout << "quad: " << indice << " -> mp: " << i << endl;
                CoppiaMPQuadrante[indice] = i;
                quadrante_raggiunto[indice] = 1;
                mp_assegnati.push_back(i);
            }
            else if (quadrante_raggiunto[indice] == 0)
            {
                indice = indice + num_colonne;
                if (indice == n_braccia_utilizzate)
                {
                    indice--;
                }
                cout << "quad: " << indice << " -> mp: " << i << endl;
                CoppiaMPQuadrante[indice] = i;
                quadrante_raggiunto[indice] = 1;
                mp_assegnati.push_back(i);
            }
        }
    }

    int temp = QuadrantiRaggiunti(quadrante_raggiunto);
    int mp_libero = 0;

    if (temp == 0) // qualche quadrante mancante
    {
        // cout << "verifica" << endl; // mettere a posto ------------------------------------------------------------------------

        for (int i = 0; i < n_braccia_utilizzate; i++)
        {
            if (quadrante_raggiunto[i] == 0)
            {
                // cout << "quadrante " << i << " libero" << endl;
                mp_libero = CercaMPLibero(&mp_assegnati);
                // cout << "   mp libero: " << mp_libero << endl;
                // cout << "lib quad: " << i << " -> mp: " << mp_libero << endl;
                CoppiaMPQuadrante[i] = mp_libero;
            }
        }
    }
}

vector<vector<int>> istruzioni::OrdinaTaskPerPunteggioPerQuadrante(vector<vector<int>> *task_per_quadrante)
{
    vector<vector<int>> temp(n_braccia_utilizzate);
    vector<vector<int>> temp2 = (*task_per_quadrante); // temp2 copia di tutte task per quad
    int indice = 0;
    int dim_temp = 0;

    for (int i = 0; i < n_braccia_utilizzate; i++)
    {
        dim_temp = temp2[i].size();
        for (int j = 0; j < dim_temp; j++)
        {
            indice = TrovaPunteggioMax(&temp2[i], i, task_per_quadrante);
            // cout << "indice max " << indice << endl;
            temp[i].push_back(indice);
        }
    }

    // cout << "dim temp: " << temp[0].size() << endl;

    // cout << "stampa prova temp che fa return: ";

    // for (unsigned l = 0; l < temp[1].size(); l++)
    // {
    //     cout << temp[1][l] << " ";
    // }
    // cout << endl;

    return temp;
}

vector<vector<int>> istruzioni::OrdinaTaskPerLunghezzaPerQuadrante(vector<vector<int>> *task_per_quadrante)
{
    int mp_scelto;
    vector<pair<int, int>> partenza;
    vector<vector<int>> lunghezze_percorsi(n_braccia_utilizzate);
    vector<vector<int>> temp(n_braccia_utilizzate);
    int indice = 0;
    int dim_vett_task = 0;
    int indice_task = 0;

    for (int i = 0; i < n_braccia_utilizzate; i++) // calcolo le lunghezze percorsi
    {
        mp_scelto = CoppiaMPQuadrante[i];
        partenza.push_back(mount_point[mp_scelto]);

        for (unsigned l = 0; l < (*task_per_quadrante)[i].size(); l++)
        {
            int dist_temp = 0;
            indice = (*task_per_quadrante)[i][l];
            for (unsigned k = 0; k < task_i[indice].pos.size(); k++)
            {
                if (k == 0)
                {
                    dist_temp += Distanza(partenza[i], task_i[indice].pos[k]);
                    // cout << "   dist temp: " << dist_temp << endl;
                }
                else
                {
                    // pos1
                    dist_temp += Distanza(task_i[indice].pos[k - 1], task_i[indice].pos[k]);
                    // cout << "   dist temp: " << dist_temp << endl;
                }
            }

            // cout << "i = " << i << " - l = " << l << " - dist = " << dist_temp << endl;
            lunghezze_percorsi[i].push_back(dist_temp);
        }
    }

    for (int l = 0; l < n_braccia_utilizzate; l++)
    {
        dim_vett_task = (*task_per_quadrante)[l].size();
        // cout << "l: " << l << " --> dim_vet: " << dim_vett_task << endl;
        for (int j = 0; j < dim_vett_task; j++)
        {
            indice_task = TrovaLunghezzaMin(task_per_quadrante, l, &lunghezze_percorsi);
            // cout << "indice task: " << indice_task << endl;
            temp[l].push_back(indice_task);
        }
    }

    return temp;
}

int istruzioni::QuadrantiRaggiunti(vector<int> quadrante_raggiunto)
{
    for (unsigned i = 0; i < quadrante_raggiunto.size(); i++)
    {
        if (quadrante_raggiunto[i] == 0)
        {
            return 0; // abbiamo uno vuoto
        }
    }

    return 1;
}

int istruzioni::MassimoVettore(vector<int> vettore)
{
    auto maxElement = max_element(vettore.begin(), vettore.end());

    int ValMax = *maxElement;

    vettore.erase(maxElement);

    return ValMax;
}

int istruzioni::TrovaPunteggioMax(vector<int> *temp, int i, vector<vector<int>> *task_per_quadrante)
{

    int max = 0;
    int ret = 0;
    int assegnato = 0;
    // int prova = (*temp).size();
    // cout << "prova: " << prova << endl;

    for (unsigned j = 0; j < (*temp).size(); j++)
    {
        int indice = (*task_per_quadrante)[i][j];
        // cout << "   indice: " << indice << endl;
        // cout << "   " << task_i[indice].punteggio << "-" << task_i[max].punteggio << endl;

        if (assegnato == 0 && (*temp)[j] >= 0)
        {
            max = j;
            ret = indice;
            assegnato = 1;
            // cout << "           dentro assegnato=0 --> max: " << ret << " j: " << j << endl;
        }
        else if (task_i[indice].punteggio > task_i[max].punteggio && (*temp)[j] >= 0)
        {
            max = j;
            ret = indice;
            // cout << "           dentro maggiore --> max: " << ret << endl;
        }
    }

    (*temp)[max] = -1;
    // cout << "max: " << max << endl;
    // (*temp).erase((*temp).begin() + max);
    // cout << "provaaaa: " << (*temp).size() << endl;
    return ret;
}

int istruzioni::TrovaLunghezzaMin(vector<vector<int>> *task_per_quadrante, int quad, vector<vector<int>> *lunghezza_percorsi)
{
    int min = 0;
    int ret = 0;
    int assegnato = 0;

    for (unsigned i = 0; i < (*task_per_quadrante)[quad].size(); i++)
    {
        // cout << (*lunghezza_percorsi)[quad][i] << " - " << (*lunghezza_percorsi)[quad][min] << endl;
        if (assegnato == 0 && (*lunghezza_percorsi)[quad][i] > 0)
        {
            min = i;
            ret = (*task_per_quadrante)[quad][i];
            assegnato = 1;
        }
        else if ((*lunghezza_percorsi)[quad][i] < (*lunghezza_percorsi)[quad][min] && (*lunghezza_percorsi)[quad][i] > 0)
        {
            // cout << "   dentro" << endl;
            min = i;
            ret = (*task_per_quadrante)[quad][i];
        }
    }

    (*lunghezza_percorsi)[quad][min] = -1;

    return ret;
}

void istruzioni::Instradamento(int num_step, vector<vector<int>> valori_g, vector<vector<int>> *task_per_quadrante, ofstream &output)
{
    int mp_scelto;
    vector<pair<int, int>> temp;
    int count = 0;
    pos_attuale.resize(n_braccia_utilizzate);
    raggiunto.resize(n_braccia_utilizzate);
    vector<vector<int>> strada_percorsa(n_braccia_utilizzate);

    for (int i = 0; i < n_braccia_utilizzate; i++)
    {
        mp_scelto = CoppiaMPQuadrante[i];
        temp.push_back(mount_point[mp_scelto]); // temp corrisponde alla partenza
        pos_attuale[i] = temp[i];
        // cout << "dim: " << (*task_per_quadrante)[i].size() << endl;
        // raggiunto[i].resize((*task_per_quadrante)[i].size());
        for (unsigned k = 0; k < (*task_per_quadrante)[i].size(); k++)
        {
            raggiunto[i].push_back(make_pair(0, 0));
        }
        sottopunto_raggiunto.push_back(0);

        cout << "braccio nel quad: " << i << " -> pos_iniziale: " << pos_attuale[i].first << " " << pos_attuale[i].second << endl;
    }

    while (count < num_step) /*|| FinitoPercorsi() == 0*/
    {
        output << count + 1 << ") ";

        if (count < 9)
        {
            output << "  ";
        }
        else if (count >= 9 && count < 99)
        {
            output << " ";
        }

        for (int j = 0; j < n_braccia_utilizzate; j++)
        {
            AvanzaUnoStep(j, &valori_g, temp[j], task_per_quadrante, &strada_percorsa, output);
        }
        count++;
        output << endl;

        // for (int j = (h - 1); j >= 0; j--)
        // {
        //     for (int i = 0; i < w; i++)
        //     {
        //         // cout << "w: " << i << " h: " << j << " " << g.valori_griglia[i][j] << endl;
        //         cout << valori_g[i][j];
        //     }
        //     cout << " " << j;
        //     cout << endl;
        // }
    }
}

void istruzioni::AvanzaUnoStep(int j, vector<vector<int>> *valori_g, pair<int, int> partenza, vector<vector<int>> *task_per_quadrante, vector<vector<int>> *strada_percorsa, ofstream &output)
{
    unsigned i = 0;
    int x, y = 0;

    x = pos_attuale[j].first;
    y = pos_attuale[j].second;

    int task_da_fare = TrovaIlPrimoZero(j);

    // cout << "task_da_fare: " << task_da_fare << endl;

    if (raggiunto[j][task_da_fare].first == 0 && task_da_fare != -1)
    {
        // for (int i = 0; i < task_i[1].num_ass_point; i++)

        // vedere di fare anche i mount_point successivi <-----------------------------------------

        // cout << "incastro 3" << endl;
        i = sottopunto_raggiunto[j];
        // cout << "   i -> " << i << "  j -> " << j << endl;

        int indice = (*task_per_quadrante)[j][task_da_fare]; // al posto di zero qui va "raggiunto"
        // cout << "indice " << indice << endl;
        // cout << "1 pos: " << task_i[indice].pos[0].first << " " << task_i[indice].pos[0].second << endl;
        // cout << endl;

        if (pos_attuale[j].first < task_i[indice].pos[i].first && (*valori_g)[x + 1][y] == LIB)
        {
            // cout << "braccio " << j << ") R" << endl;
            output << "R ";
            (*strada_percorsa)[j].push_back(R);
            pos_attuale[j].first++;
            (*valori_g)[x + 1][y] = OCC;
            // cout << "   occupo pos " << x + 1 << "--" << y << endl;
        }
        else if (pos_attuale[j].first > task_i[indice].pos[i].first && (*valori_g)[x - 1][y] == LIB)
        {
            // cout << "braccio " << j << ") L" << endl;
            output << "L ";
            (*strada_percorsa)[j].push_back(L);
            pos_attuale[j].first--;
            (*valori_g)[x - 1][y] = OCC;
            // cout << "   occupo pos " << x - 1 << "--" << y << endl;
        }
        else if (pos_attuale[j].second < task_i[indice].pos[i].second && (*valori_g)[x][y + 1] == LIB)
        {
            // cout << "braccio " << j << ") U" << endl;
            output << "U ";
            (*strada_percorsa)[j].push_back(U);
            pos_attuale[j].second++;
            (*valori_g)[x][y + 1] = OCC;
            // cout << "   occupo pos " << x << "--" << y + 1 << endl;
        }
        else if (pos_attuale[j].second > task_i[indice].pos[i].second && (*valori_g)[x][y - 1] == LIB)
        {
            // cout << "braccio " << j << ") D" << endl;
            output << "D ";
            (*strada_percorsa)[j].push_back(D);
            pos_attuale[j].second--;
            (*valori_g)[x][y - 1] = OCC;
            // cout << "   occupo pos " << x << "--" << y - 1 << endl;
        }
        else
        {
            // cout << "braccio " << j << ") rimango fermo" << endl;
            output << "- ";
        }

        if (pos_attuale[j] == task_i[indice].pos[i])
        {
            // cout << "incastro 4" << endl;
            // cout << "       task_i[j].pos.size() -> " << task_i[j].pos.size() << " - " << i << endl;
            if (i == (task_i[indice].pos.size() - 1))
            {
                raggiunto[j][task_da_fare].first = 1;
                // cout << "incastro 1" << endl;
                cout << "               Finita task " << indice << " con " << task_i[indice].punteggio << " punti" << endl;
                punteggio_totale += task_i[indice].punteggio;
                num_task_compl++;
            }
            else
            {
                // cout << "incastro 2" << endl;
                sottopunto_raggiunto[j]++;
            }

            // cerr << "STOP" << endl;
        }
    }
    else if (raggiunto[j][task_da_fare].second != 1 && task_da_fare != -1) /* (raggiunto[j].first != 0)*/
    {
        // cout << "   ritorno braccio: " << j << ") ";

        if (pos_attuale[j] != partenza && raggiunto[j][task_da_fare].second != 1)
        {
            // cout << "   dim str_p: " << (*strada_percorsa)[j].size() << endl;
            int valore_temp = (*strada_percorsa)[j].back();
            (*strada_percorsa)[j].pop_back();

            cout << "x: " << x << " y: " << y << endl;
            // cout << "dim valori_g: " << (*valori_g).size() << " dim valori_g[x]: " << (*valori_g)[x].size() << endl;
            if (static_cast<unsigned int>(x) >= (*valori_g).size())
            {
                cout << "dim sbagliata x: " << x << endl;
                exit(1);
            }
            if (static_cast<unsigned int>(y) >= (*valori_g)[x].size())
            {
                cout << "dim sbagliata y: " << y << endl;
                exit(1);
            }

            switch (valore_temp)
            {
            case R:
                pos_attuale[j].first--;
                (*valori_g)[x][y] = LIB;
                // cout << "   libero pos " << x << "--" << y << endl;
                // cout << "   L " << endl;
                output << "L ";
                break;
            case L:
                pos_attuale[j].first++;
                (*valori_g)[x][y] = LIB;
                // cout << "   libero pos " << x << "--" << y << endl;
                // cout << "   R " << endl;
                output << "R ";
                break;
            case U:
                pos_attuale[j].second--;
                (*valori_g)[x][y] = LIB;
                // cout << "   libero pos " << x << "--" << y << endl;
                // cout << "   D " << endl;
                output << "D ";
                break;
            case D:
                pos_attuale[j].second++;
                (*valori_g)[x][y] = LIB;
                // cout << "   libero pos " << x << "--" << y << endl;
                // cout << "   U  " << endl;
                output << "U ";
                break;
            }
            // cout << "   pos_attuale: " << pos_attuale[j].first << " " << pos_attuale[j].second << endl;
        }

        if (pos_attuale[j] == partenza && raggiunto[j][task_da_fare].second != 1)
        {
            cout << "       tornato alla base braccio " << j << " pos: " << pos_attuale[j].first << " " << pos_attuale[j].second << endl;
            raggiunto[j][task_da_fare].second = 1;
        }
    }
}

int istruzioni::TrovaIlPrimoZero(int j)
{
    int valore = -1;

    // cout << "   raggiunto " << j << " " << raggiunto[j].size() << endl;

    for (unsigned i = 0; i < raggiunto[j].size(); i++)
    {
        // cout << "verifica: " << raggiunto[j][i].first << " " << raggiunto[j][i].second << endl;
        if (raggiunto[j][i].second == 0)
        {
            valore = i;
            return valore;
        }
    }

    return valore;
}

bool operator!=(const pair<int, int> &a, const pair<int, int> &b)
{
    return (a.first != b.first) || (a.second != b.second);
}

bool operator==(const pair<int, int> &a, const pair<int, int> &b)
{
    return (a.first == b.first) && (a.second == b.second);
}

int istruzioni::CercaMPLibero(vector<int> *mp_assegnati)
{
    vector<int> vettore(mount_point.size(), 0);
    int num = 0;
    // cout << "dim: " << (*mp_assegnati).size() << endl;

    for (unsigned i = 0; i < (*mp_assegnati).size(); i++)
    {
        // cout << "       " << (*mp_assegnati)[i] << " ";
        vettore[(*mp_assegnati)[i]] = 1;
    }

    for (unsigned j = 0; j < vettore.size(); j++)
    {
        // cout << "       " << vettore[j] << " ";

        if (vettore[j] == 0)
        {
            num = j;
            (*mp_assegnati).push_back(num);
            return num;
        }
    }

    // cout << endl;

    return num;
}

int istruzioni::Distanza(pair<int, int> pos1, pair<int, int> pos2)
{
    int ris = abs(pos1.first - pos2.first) + abs(pos1.second - pos2.second);
    return ris;
}