using System;
using System.Collections.Generic;

// Diagramas N/V/M de UN elemento del visor, reconstruidos a partir de las
// fuerzas locales que exporto el FE (analysis_map.json -> forces[caso][tag].li/lj).
//
// QUE CARGA APLICA EL FE (verificado en opensees_edificio_v2.py):
//   * Peso propio: cargas NODALES W/2 en cada extremo (no es carga distribuida).
//   * Losa + tributarias: SOLO en vigas, uniforme, eleLoad beamUniform Wy=0, Wz=-q.
//     Wy=0 => en el plano local x-y NO hay carga distribuida; el -q*x^2/2 solo
//     existe en el plano x-z. Este es el error clasico al dibujar los dos planos.
//   * EX / EY: sin carga distribuida sobre el elemento.
//
// EJES LOCALES (geomTransf en opensees_edificio_v2.py):
//   transf 2 (vecxz=(0,0,1)) -> vigas de hormigon: xz local = vertical.
//   transf 1 (vecxz=(1,0,0)) -> columnas, muros y acero: x local = vertical,
//     asi que sus dos planos (x-z, x-y) son HORIZONTALES ambos.
//
// De ahi, con x medido desde el nodo i hacia el nodo j (m):
//   plano x-z: N(x) = N_i | Vz(x) = Vz_i - q*x | My(x) = My_i + Vz_i*x - q*x^2/2
//   plano x-y: N(x) = N_i | Vy(x) = Vy_i     | Mz(x) = Mz_i - Vy_i*x
//
// OJO con el signo del momento: el cortante entra con +Vz en My y con -Vy en
// Mz. El error tipico es usar +Vy en el plano horizontal; no cierra en muros ni
// en el segundo plano de las vigas (residuo relativo ~1e+02, no ~1e-08).
//
// CIERRES (verificados sobre el modelo real: 701 elementos en los 5 casos,
// ajustando el signo s de dM/dx = s*V por tipo de elemento; s=+1 en My y
// s=-1 en Mz, con residuo relativo maximo 1.2e-05, que es el redondeo a
// 6 decimales de p):
//   N_i + N_j = 0 | Vy_i + Vy_j = 0 | Vz_i + Vz_j = q*L
//   My(L) = -My_j | Mz(L) = -Mz_j
// El residuo se recalcula aqui y se muestra en la ficha: si el JSON no cerrara
// se ve en pantalla, en vez de dibujar un diagrama incorrecto sin avisar.
//
// q por caso (kN/m), con los factores VIVOS de la superposicion:
//   G = pG | Q = pQ | EX = 0 | EY = 0
//   COMBO = lambda_G*pG + lambda_Q*pQ
// (lambda = AnalysisMap.Lambdas, que cambian con los sliders; NO se fijan a
// 1.2/1.0 para no desincronizar q de las fuerzas en Forces["COMBO"]).
public static class ElementDiagrams
{
    public const string SinResultados = "Sin resultados para este elemento y caso";

    public const int PlanoVertical = 0;    // Vz / My  (plano x-z: cortante vertical)
    public const int PlanoHorizontal = 1;  // Vy / Mz  (plano x-y: horizontal)

    const int MuestrasPorTramo = 25;       // resolucion dentro de cada tramo FE

    // Indices dentro de EndForces.li / .lj: 0=N 1=Vy 2=Vz 3=T 4=My 5=Mz
    const int N_IDX = 0, VY_IDX = 1, VZ_IDX = 2, MY_IDX = 4, MZ_IDX = 5;

    public class Resultado
    {
        public AnalysisMap.DiagInfo diag;
        public string error;         // null si se pudo construir
        public double q;             // kN/m realmente aplicado en este caso
        public double L;             // m, longitud total concatenada
        public int tramos;           // segmentos FE que componen el elemento
        public bool esViga;
        public double residN;        // residuos de cierre, relativo
        public double residV;
        public double residM;
        public double errN;          // los mismos residuos en unidades fisicas
        public double errV;          // kN
        public double errM;          // kN*m
    }

    struct Tramo
    {
        public int tag;              // tag del elemento en el FE
        public int ni, nj;           // nodos del FE
        public double L;             // m
        public double q;             // kN/m en este caso
        public double[] li, lj;      // [N, Vy, Vz, T, My, Mz]
    }

    public static Resultado Construir(int contractTag, string caso, int plano)
    {
        var r = new Resultado { error = SinResultados };
        if (!AnalysisMap.Loaded) return r;

        AnalysisMap.ElementInfo meta = AnalysisMap.Element(contractTag);
        if (meta == null) return r;

        // Solo beam_x/beam_y reciben la carga de losa por area tributaria
        // (las vigas MET no tienen entrada en `tributarias` del contrato).
        r.esViga = meta.type == "beam_x" || meta.type == "beam_y";

        List<Tramo> tramos = Tramos(meta, caso, r.esViga);
        if (tramos.Count == 0) return r;

        // Una viga subdividida son varios elementos en el FE. Si falta alguno
        // (o su longitud), el diagrama seria incompleto: mejor no dibujarlo.
        int esperados = 1;
        List<AnalysisMap.BeamFraction> fracs;
        if (AnalysisMap.BeamFractionElems != null &&
            AnalysisMap.BeamFractionElems.TryGetValue(meta.id, out fracs) &&
            fracs != null && fracs.Count > 0) esperados = fracs.Count;
        if (tramos.Count < esperados) return r;

        r.tramos = tramos.Count;
        r.q = tramos[0].q;

        // Muestreo por tramo: extremos + uniforme + el punto de cortante nulo
        // (x* = V/q), que es donde M alcanza su extremum, para que el marcador
        // de maximo del grafico no dependa de la discretizacion.
        var xs = new List<double>();
        var N = new List<double>();
        var V = new List<double>();
        var M = new List<double>();
        double Ltotal = 0.0;

        bool horizontal = plano == PlanoHorizontal;
        // El FE aplica la carga de losa como beamUniform Wy=0, Wz=-q: la carga
        // uniforme SOLO existe en el plano local x-z (Vz / My). En el plano x-y
        // (Vy / Mz) no hay nada distribuido porque Wy=0.
        bool conQ = !horizontal;
        // Signo del termino cortante en el momento, medido contra las fuerzas
        // reales del FE en los 701 elementos x 5 casos: dMy/dx = +Vz y
        // dMz/dx = -Vy (no es el mismo signo en los dos planos).
        double sgn = horizontal ? -1.0 : 1.0;
        for (int t = 0; t < tramos.Count; t++)
        {
            Tramo s = tramos[t];
            if (s.L <= 1e-9) continue;

            double Nv = s.li[N_IDX];
            double Vi = s.li[horizontal ? VY_IDX : VZ_IDX];
            double Mi = s.li[horizontal ? MZ_IDX : MY_IDX];
            double q = s.q;

            var loc = new List<double>();
            for (int i = 0; i <= MuestrasPorTramo; i++) loc.Add(s.L * i / MuestrasPorTramo);
            if (conQ && Math.Abs(q) > 1e-12)
            {
                double xv = Vi / q;                    // dMy/dx = Vz = 0
                if (xv > 1e-9 && xv < s.L - 1e-9) loc.Add(xv);
            }
            loc.Sort();

            for (int i = 0; i < loc.Count; i++)
            {
                double x = loc[i];
                xs.Add(Ltotal + x);
                N.Add(Nv);
                V.Add(Vi - (conQ ? q * x : 0.0));
                M.Add(Mi + sgn * Vi * x - (conQ ? 0.5 * q * x * x : 0.0));
            }
            Ltotal += s.L;
        }

        if (xs.Count < 2 || Ltotal <= 0.0) return r;

        double absN, absV, absM;
        r.residN = Residuo(tramos, N_IDX, false, false, out absN);
        r.residV = Residuo(tramos, horizontal ? VY_IDX : VZ_IDX, conQ, false, out absV);
        r.residM = Residuo(tramos, horizontal ? MZ_IDX : MY_IDX, conQ, true, out absM);
        r.errN = absN; r.errV = absV; r.errM = absM;
        r.L = Ltotal;

        AnalysisMap.DiagInfo d = new AnalysisMap.DiagInfo();
        d.tag = contractTag;
        d.tipo = meta.type;
        d.seccion = meta.section;
        d.L = Ltotal;
        d.x = xs.ToArray();
        d.N = N.ToArray();
        d.V = V.ToArray();
        d.M = M.ToArray();
        d.hasQ = r.esViga;
        d.q = r.q;
        d.resid = Math.Max(r.residV, r.residM);
        d.resMJ = r.residN;
        r.diag = d;
        r.error = null;
        return r;
    }

    // Tramos FE del elemento. Una viga subdividida son N elementos en el FE; el
    // visor la dibuja como una sola pieza con el id del contrato, asi que el
    // diagrama se arma concatenando sus fracciones EN ORDEN.
    static List<Tramo> Tramos(AnalysisMap.ElementInfo meta, string caso, bool esViga)
    {
        var list = new List<Tramo>();
        List<AnalysisMap.BeamFraction> fracs;
        if (AnalysisMap.BeamFractionElems != null &&
            AnalysisMap.BeamFractionElems.TryGetValue(meta.id, out fracs) &&
            fracs != null && fracs.Count > 0)
        {
            for (int i = 0; i < fracs.Count; i++)
                Add(list, caso, fracs[i].tag, fracs[i].ni, fracs[i].nj, esViga, meta.id);
        }
        else
        {
            // Sin subdivision: el tag del FE coincide con el id del contrato.
            Add(list, caso, meta.id, meta.ni, meta.nj, esViga, meta.id);
        }
        return list;
    }

    static void Add(List<Tramo> list, string caso, int tag, int ni, int nj, bool esViga, int parent)
    {
        AnalysisMap.EndForces f = AnalysisMap.Fuerzas(caso, tag);
        if (f == null || f.li == null || f.lj == null || f.li.Length < 6 || f.lj.Length < 6) return;
        double L = Distancia(ni, nj);
        if (L <= 0.0) return;
        list.Add(new Tramo
        {
            tag = tag,
            ni = ni,
            nj = nj,
            L = L,
            q = qDeCaso(caso, parent, esViga),
            li = f.li,
            lj = f.lj
        });
    }

    static double qDeCaso(string caso, int parent, bool esViga)
    {
        if (!esViga) return 0.0;                    // columna / muro / viga MET
        AnalysisMap.TribuInfo t = AnalysisMap.Tributaria(parent);
        if (t == null) return 0.0;
        if (caso == "G") return t.pG;
        if (caso == "Q") return t.pQ;
        if (caso == "COMBO")
        {
            double[] lam = AnalysisMap.Lambdas;     // factores vivos de la superposicion
            double lg = (lam != null && lam.Length > 0) ? lam[0] : 1.2;
            double lq = (lam != null && lam.Length > 1) ? lam[1] : 1.0;
            return lg * t.pG + lq * t.pQ;
        }
        return 0.0;                                 // EX / EY
    }

    static double Distancia(int ni, int nj)
    {
        double[] a, b;
        if (AnalysisMap.StructCoords == null ||
            !AnalysisMap.StructCoords.TryGetValue(ni.ToString(), out a) ||
            !AnalysisMap.StructCoords.TryGetValue(nj.ToString(), out b) ||
            a == null || b == null || a.Length < 3 || b.Length < 3) return 0.0;
        double dx = a[0] - b[0], dy = a[1] - b[1], dz = a[2] - b[2];
        return Math.Sqrt(dx * dx + dy * dy + dz * dz);
    }

    // Residuo del cierre del tramo para un componente, en dos lecturas:
    //   absoluto  (out abs): el error tal cual, en kN o kN*m
    //   relativo  (return) : el error dividido por la escala del efecto
    // La escala es el propio efecto y como minimo 1.0, para que un momento
    // casi nulo no dispare una falsa alarma. Por eso el criterio de aceptacion
    // se apoya en el error ABSOLUTO (tolerancia 1e-4 kN / kN*m, unas 3 veces
    // por encima del peor error real medido y del error de redondeo de p).
    // conQ = "la carga uniforme q actua en este plano" (solo el plano x-z).
    //   momento  (momento):  M(L) desde i contra M_j       (M(L) == -M_j)
    //   cortante (conQ):     V_i + V_j contra q*L          (V_i + V_j == q*L)
    //   cortante (sin q):    V_i + V_j contra 0            (Vy: Wy = 0)
    //   axial:               N_i + N_j contra 0            (sin carga axial repartida)
    static double Residuo(List<Tramo> tramos, int indice, bool conQ, bool momento, out double peorAbs)
    {
        double peor = 0.0;
        peorAbs = 0.0;
        for (int t = 0; t < tramos.Count; t++)
        {
            Tramo s = tramos[t];
            double error, escala;
            if (momento)
            {
                // dMy/dx = +Vz   |   dMz/dx = -Vy  (ajustado a las fuerzas del FE)
                double b = (indice == MZ_IDX) ? -s.li[VY_IDX] : s.li[VZ_IDX];
                double ML = s.li[indice] + b * s.L - (conQ ? 0.5 * s.q * s.L * s.L : 0.0);
                error = Math.Abs(ML + s.lj[indice]);
                escala = Math.Max(Math.Abs(s.lj[indice]), 1.0);
            }
            else if (conQ)
            {
                double objetivo = s.q * s.L;
                error = Math.Abs(s.li[indice] + s.lj[indice] - objetivo);
                escala = Math.Max(Math.Abs(objetivo), 1.0);
            }
            else
            {
                error = Math.Abs(s.li[indice] + s.lj[indice]);
                escala = Math.Max(Math.Max(Math.Abs(s.li[indice]), Math.Abs(s.lj[indice])), 1.0);
            }
            if (error > peorAbs) peorAbs = error;
            double rel = error / escala;
            if (rel > peor) peor = rel;
        }
        return peor;
    }
}
