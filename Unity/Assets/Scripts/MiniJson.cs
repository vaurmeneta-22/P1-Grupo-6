using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

// Mini parser JSON (sin dependencias). Soporta objetos, arreglos, strings con
// escapes (\uXXXX incluido), numeros (float/entero/exponente), true/false/null.
// Devuelve: Dictionary<string,object>, List<object>, string, double, bool, null.
public static class MiniJson
{
    public static object Parse(string text)
    {
        int i = 0;
        SkipWs(text, ref i);
        object v = ParseValue(text, ref i);
        return v;
    }

    public static bool TryParse(string text, out object value)
    {
        try { value = Parse(text); return true; }
        catch (System.Exception) { value = null; return false; }
    }

    // ---------- Accesos de conveniencia ----------

    public static Dictionary<string, object> AsDict(object o)
    {
        return o as Dictionary<string, object>;
    }

    public static List<object> AsList(object o)
    {
        return o as List<object>;
    }

    public static string Str(object o)
    {
        return o as string;
    }

    public static bool Bool(object o)
    {
        if (o is bool) return (bool)o;
        return false;
    }

    public static double Num(object o)
    {
        if (o is double) return (double)o;
        if (o is float) return (float)o;
        if (o is int) return (int)o;
        if (o is long) return (long)o;
        return 0.0;
    }

    public static object Get(object obj, string key)
    {
        Dictionary<string, object> d = AsDict(obj);
        object v;
        if (d != null && d.TryGetValue(key, out v)) return v;
        return null;
    }

    public static Dictionary<string, object> Dict(object obj, string key)
    {
        return AsDict(Get(obj, key));
    }

    public static List<object> Lis(object obj, string key)
    {
        return AsList(Get(obj, key));
    }

    public static double Db(object obj, string key)
    {
        return Num(Get(obj, key));
    }

    public static bool Bt(object obj, string key)
    {
        return Bool(Get(obj, key));
    }

    public static string St(object obj, string key)
    {
        return Str(Get(obj, key));
    }

    public static double[] NumArray(object obj, string key)
    {
        List<object> l = AsList(Get(obj, key));
        if (l == null) return new double[0];
        double[] r = new double[l.Count];
        for (int i = 0; i < l.Count; i++) r[i] = Num(l[i]);
        return r;
    }

    public static double[] NumArrayValue(object o)
    {
        List<object> l = AsList(o);
        if (l == null) return new double[0];
        double[] r = new double[l.Count];
        for (int i = 0; i < l.Count; i++) r[i] = Num(l[i]);
        return r;
    }

    // ---------- Parser ----------

    static void SkipWs(string s, ref int i)
    {
        while (i < s.Length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) i++;
    }

    static object ParseValue(string s, ref int i)
    {
        SkipWs(s, ref i);
        if (i >= s.Length) throw new FormatException("JSON inesperado: fin de entrada");
        char c = s[i];
        switch (c)
        {
            case '{': return ParseObject(s, ref i);
            case '[': return ParseArray(s, ref i);
            case '"': return ParseString(s, ref i);
            case 't':
                Expect(s, ref i, "true");
                return true;
            case 'f':
                Expect(s, ref i, "false");
                return false;
            case 'n':
                Expect(s, ref i, "null");
                return null;
            default: return ParseNumber(s, ref i);
        }
    }

    static Dictionary<string, object> ParseObject(string s, ref int i)
    {
        i++; // '{'
        Dictionary<string, object> d = new Dictionary<string, object>();
        SkipWs(s, ref i);
        if (i < s.Length && s[i] == '}') { i++; return d; }
        while (true)
        {
            SkipWs(s, ref i);
            string key = ParseString(s, ref i); // las claves siempre van entre comillas
            SkipWs(s, ref i);
            if (i >= s.Length || s[i] != ':') throw new FormatException("Falta ':' en objeto");
            i++;
            object val = ParseValue(s, ref i);
            d[key] = val;
            SkipWs(s, ref i);
            if (i >= s.Length) throw new FormatException("JSON truncado en objeto");
            if (s[i] == ',') { i++; continue; }
            if (s[i] == '}') { i++; return d; }
            throw new FormatException("Se esperaba ',' o '}'");
        }
    }

    static List<object> ParseArray(string s, ref int i)
    {
        i++; // '['
        List<object> l = new List<object>();
        SkipWs(s, ref i);
        if (i < s.Length && s[i] == ']') { i++; return l; }
        while (true)
        {
            object val = ParseValue(s, ref i);
            l.Add(val);
            SkipWs(s, ref i);
            if (i >= s.Length) throw new FormatException("JSON truncado en arreglo");
            if (s[i] == ',') { i++; continue; }
            if (s[i] == ']') { i++; return l; }
            throw new FormatException("Se esperaba ',' o ']'");
        }
    }

    static string ParseString(string s, ref int i)
    {
        if (i >= s.Length || s[i] != '"') throw new FormatException("Se esperaba string");
        i++;
        StringBuilder sb = new StringBuilder();
        while (i < s.Length)
        {
            char c = s[i++];
            if (c == '"') return sb.ToString();
            if (c == '\\')
            {
                if (i >= s.Length) break;
                char e = s[i++];
                switch (e)
                {
                    case '"': sb.Append('"'); break;
                    case '\\': sb.Append('\\'); break;
                    case '/': sb.Append('/'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'n': sb.Append('\n'); break;
                    case 'r': sb.Append('\r'); break;
                    case 't': sb.Append('\t'); break;
                    case 'u':
                        if (i + 4 <= s.Length)
                        {
                            string hex = s.Substring(i, 4);
                            sb.Append((char)ushort.Parse(hex, NumberStyles.HexNumber));
                            i += 4;
                        }
                        break;
                    default: sb.Append(e); break;
                }
            }
            else
            {
                sb.Append(c);
            }
        }
        throw new FormatException("String sin cerrar");
    }

    static void Expect(string s, ref int i, string word)
    {
        if (i + word.Length > s.Length || s.Substring(i, word.Length) != word)
            throw new FormatException("Token inesperado: " + word);
        i += word.Length;
    }

    static object ParseNumber(string s, ref int i)
    {
        int start = i;
        if (i < s.Length && s[i] == '-') i++;
        while (i < s.Length && char.IsDigit(s[i])) i++;
        if (i < s.Length && s[i] == '.')
        {
            i++;
            while (i < s.Length && char.IsDigit(s[i])) i++;
        }
        if (i < s.Length && (s[i] == 'e' || s[i] == 'E'))
        {
            i++;
            if (i < s.Length && (s[i] == '+' || s[i] == '-')) i++;
            while (i < s.Length && char.IsDigit(s[i])) i++;
        }
        string tok = s.Substring(start, i - start);
        double v;
        if (double.TryParse(tok, NumberStyles.Float, CultureInfo.InvariantCulture, out v))
            return v;
        throw new FormatException("Numero invalido: " + tok);
    }
}