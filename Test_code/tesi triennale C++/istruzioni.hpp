#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <cmath>

#define OCC 1
#define LIB 0

using namespace std;

class istruzioni
{

    friend ostream &operator<<(ostream &os, const istruzioni &i);
    friend ostream &operator<<(ostream &os, const vector<vector<int>> &valori_g);
    friend bool operator!=(const pair<int, int> &a, const pair<int, int> &b);
    friend bool operator==(const pair<int, int> &a, const pair<int, int> &b);

public:
    istruzioni(const griglia &g);

    int n_braccia_utilizzate; // numero braccia da usare
    vector<lavoro> task_i;
    int num_task;
    int num_step;
    int h;
    int w;
    vector<pair<int, int>> mount_point;
    vector<vector<int>> valori_g;
    vector<int> CoppiaMPQuadrante;
    vector<pair<int, int>> pos_attuale;
    vector<int> sottopunto_raggiunto;         // serve per arrivare a tutti mp
    vector<vector<pair<int, int>>> raggiunto; // per ogni braccio (mi tengo anche a che task arrivo), first se arrivo in fondo, second se torno a base
    int punteggio_totale;
    int num_task_compl;

    void SuddivisioneGriglia(vector<vector<int>> *task_per_quadrante);
    void AccoppiaMPQuadrante();
    int QuadrantiRaggiunti(vector<int> quadrante_raggiunto);
    vector<vector<int>> OrdinaTaskPerPunteggioPerQuadrante(vector<vector<int>> *task_per_quadrante);
    vector<vector<int>> OrdinaTaskPerLunghezzaPerQuadrante(vector<vector<int>> *task_per_quadrante);
    int MassimoVettore(vector<int> vettore);
    int TrovaPunteggioMax(vector<int> *temp, int i, vector<vector<int>> *task_per_quadrante);
    int TrovaLunghezzaMin(vector<vector<int>> *task_per_quadrante, int quad, vector<vector<int>> *lunghezza_percorsi);
    void Instradamento(int num_step, vector<vector<int>> valori_g, vector<vector<int>> *task_per_quadrante, ofstream &output);
    void AvanzaUnoStep(int j, vector<vector<int>> *valori_g, pair<int, int> partenza, vector<vector<int>> *task_per_quadrante, vector<vector<int>> *strada_percorsa, ofstream &output);
    int TrovaIlPrimoZero(int j);
    int CercaMPLibero(vector<int> *mp_assegnati);
    int Distanza(pair<int, int> pos1, pair<int, int> pos2);
    int GetPuntTot() const { return punteggio_totale; };
    int GetNumTaskCompl() const { return num_task_compl; };
};