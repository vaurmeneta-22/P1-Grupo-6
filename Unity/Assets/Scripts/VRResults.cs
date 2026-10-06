using System;
using UnityEngine;

// Data and local-axis conventions are shared with the desktop inspector.
public class VRResults
{
    public string Case = "G";
    public int View, Plane, Sample;
    public ElementTag Selected;
    public string LastError { get; private set; }
    static readonly Color Cyan=new Color(.05f,.91f,.98f), Amber=new Color(1,.72f,.14f);
    public static string F(double v,int digits=2) { return v.ToString("F"+digits,System.Globalization.CultureInfo.InvariantCulture); }
    public static string TypeName(string t) { return t=="column"?"Columna":t=="wall"?"Muro":t.StartsWith("beam")?"Viga":t; }

    public void Render(VRWorldUI ui)
    {
        LastError=null;
        try { if(View<=2) Diagram(ui); else if(View==3) PM(ui); else MomentCurvature(ui); }
        catch(Exception ex) { Missing(ui,"No se pudo consultar el resultado: "+ex.Message); Debug.LogException(ex); }
    }

    void Missing(VRWorldUI ui,string text)
    {
        LastError=text; ui.BeginGraph(0,1,0,1,"","");
        ui.Detail.text=text; ui.Readout.text=""; ui.Notice.text="Selecciona otra vista o vuelve al recorrido.";
    }

    static void Bounds(double[] values,out double min,out double max,float sign=1)
    {
        min=0; max=0;
        foreach(double raw in values)
        {
            double v=raw*sign;
            if(double.IsNaN(v)||double.IsInfinity(v)) throw new InvalidOperationException("Datos no finitos.");
            min=Math.Min(min,v); max=Math.Max(max,v);
        }
        double pad=Math.Max((max-min)*.12,1e-5); min-=pad; max+=pad;
    }

    void Diagram(VRWorldUI ui)
    {
        var r=ElementDiagrams.Construir(Selected.elementId,Case,Plane);
        if(r.error!=null || r.diag==null) { Missing(ui,r.error ?? "Sin diagrama."); return; }
        var d=r.diag; var v=View==0?d.N:View==1?d.V:d.M;
        string quantity=View==0?"N":View==1?(Plane==0?"Vz":"Vy"):(Plane==0?"My":"Mz");
        string unit=View==2?"kN·m":"kN";
        float sign=View==2?-1:1;
        double ymin,ymax; Bounds(v,out ymin,out ymax,sign);
        ui.BeginGraph(0,d.L,ymin,ymax,"x [m]",quantity+" ["+unit+"]",sign);
        ui.Zero(0,d.L,ymin,ymax); ui.Curve(d.x,v,0,d.L,ymin,ymax,Cyan,sign);
        Sample=Mathf.Clamp(Sample,0,v.Length-1);
        ui.Mark(d.x[Sample],v[Sample]*sign,0,d.L,ymin,ymax,Amber);
        double minimum=double.PositiveInfinity,maximum=double.NegativeInfinity;
        foreach(double value in v) { minimum=Math.Min(minimum,value); maximum=Math.Max(maximum,value); }
        ui.Detail.text=quantity+" · "+Case+" · "+(Plane==0?"x-z":"x-y")+" · L="+F(d.L)+" m · "+r.tramos+" tramos FE";
        ui.Readout.text="x="+F(d.x[Sample])+" m: "+F(v[Sample])+" "+unit+"\nMín="+F(minimum)+" · Máx="+F(maximum)+" "+unit;
        ui.Notice.text=(View==2?"Momentos: negativo arriba / positivo abajo. ":"Positivo arriba / negativo abajo. ")+"\nCierre N/V/M: "+r.errN.ToString("0.0E+0")+" / "+r.errV.ToString("0.0E+0")+" / "+r.errM.ToString("0.0E+0")+" (kN / kN / kN·m).";
    }

    void PM(VRWorldUI ui)
    {
        var meta=AnalysisMap.Element(Selected.elementId);
        if(meta==null) { Missing(ui,"Elemento sin metadatos OpenSees."); return; }
        var curve=PickHighlight.CapacityCur(meta);
        if(curve==null) { Missing(ui,"P-M no disponible para "+meta.type+" "+meta.section+"."); return; }
        var p=MiniJson.NumArray(curve,"P"); var m=MiniJson.NumArray(curve,"M");
        if(p.Length<2 || p.Length!=m.Length) { Missing(ui,"Curva P-M incompleta."); return; }
        var forces=AnalysisMap.Fuerzas(Case,meta.id);
        if(forces==null) { Missing(ui,"Sin demanda OpenSees para "+Case+"."); return; }
        double pd,md; PickHighlight.DemandaPM(forces,meta,out pd,out md);
        double ymin,ymax; Bounds(p,out ymin,out ymax);
        ymin=Math.Min(ymin,pd-Math.Abs(pd)*.1); ymax=Math.Max(ymax,pd+Math.Abs(pd)*.1);
        double limit=Math.Max(1,Math.Abs(md)); foreach(double v in m) limit=Math.Max(limit,Math.Abs(v)); limit*=1.15;
        ui.BeginGraph(-limit,limit,ymin,ymax,"M [kN·m]","P [kN]"); ui.Zero(-limit,limit,ymin,ymax);
        ui.Curve(m,p,-limit,limit,ymin,ymax,Cyan);
        var mirrored=new double[m.Length]; for(int i=0;i<m.Length;i++) mirrored[i]=-m[i];
        ui.Curve(mirrored,p,-limit,limit,ymin,ymax,Cyan);
        ui.Mark(md,pd,-limit,limit,ymin,ymax,Amber);
        Sample=Mathf.Clamp(Sample,0,p.Length-1); ui.Mark(m[Sample],p[Sample],-limit,limit,ymin,ymax,Color.white);
        ui.Detail.text="P-M · "+meta.section+" · "+Case+" · curva "+(MiniJson.St(curve,"seccion")??"del visor");
        ui.Readout.text="Demanda: P="+F(pd,1)+" kN · M="+F(md,1)+" kN·m\nMuestra: P="+F(p[Sample],1)+" kN · M="+F(m[Sample],1)+" kN·m";
        ui.Notice.text="Cian: capacidad exportada. Amarillo: demanda según el criterio del visor.\nConsulta didáctica de la curva; el cálculo de capacidad es independiente del modelo global.";
    }

    void MomentCurvature(VRWorldUI ui)
    {
        var meta=AnalysisMap.Element(Selected.elementId);
        var p=AnalysisMap.MomCurv;
        if(meta==null || meta.type!="column" || meta.section!="70x70" || p==null || p.phi_1m==null || p.M_fiber==null || p.phi_1m.Length<2 || p.M_fiber.Length!=p.phi_1m.Length)
        { Missing(ui,"M-curvatura disponible únicamente como referencia de columna 70×70, P=0."); return; }
        double ymin,ymax; Bounds(p.M_fiber,out ymin,out ymax);
        double xmax=0; foreach(double x in p.phi_1m) xmax=Math.Max(xmax,x); if(xmax<=0) throw new InvalidOperationException("Curvatura no válida.");
        ui.BeginGraph(0,xmax,ymin,ymax,"φ [1/m]","M [kN·m]"); ui.Zero(0,xmax,ymin,ymax);
        ui.Curve(p.phi_1m,p.M_fiber,0,xmax,ymin,ymax,Cyan);
        Sample=Mathf.Clamp(Sample,0,p.M_fiber.Length-1); ui.Mark(p.phi_1m[Sample],p.M_fiber[Sample],0,xmax,ymin,ymax,Amber);
        ui.Detail.text="Momento-curvatura · referencia columna 70×70 · P=0";
        ui.Readout.text="φ="+F(p.phi_1m[Sample],5)+" 1/m · M="+F(p.M_fiber[Sample],1)+" kN·m\nMomento último exportado: "+F(p.M_ult,1)+" kN·m";
        ui.Notice.text="Curva de sección por fibras a P=0; no cambia con G/Q/EX/EY/COMBO.\nNo representa la curvatura calculada del elemento seleccionado.";
    }
}
