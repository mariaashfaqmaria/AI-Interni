// frontend/src/components/Calendar.jsx

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Calendar as Cal, ChevronLeft, ChevronRight, ArrowRight } from "lucide-react";
import api from "../api";
import { iso } from "../utils";
const DAYS=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
export default function Calendar(){
 const [cursor,setCursor]=useState(()=>new Date(new Date().getFullYear(),new Date().getMonth(),1));const [dots,setDots]=useState({});
 const year=cursor.getFullYear(),month=cursor.getMonth();const monthKey=`${year}-${String(month+1).padStart(2,"0")}`;
 useEffect(()=>{let alive=true;api.get("/dashboard/calendar-dots",{params:{month:monthKey}}).then(({data})=>{if(alive)setDots(data);}).catch(()=>{if(alive)setDots({});});return()=>{alive=false;};},[monthKey]);
 const startOffset=cursor.getDay();const daysInMonth=new Date(year,month+1,0).getDate();const today=new Date();const isToday=d=>d===today.getDate()&&month===today.getMonth()&&year===today.getFullYear();const cells=[...Array(startOffset).fill(null),...Array.from({length:daysInMonth},(_,i)=>i+1)];const shift=n=>setCursor(new Date(year,month+n,1));
 return <section className="card"><div className="card-head"><h3 className="card-title"><Cal size={20} className="accent"/> Project Schedule</h3><Link className="link" to="/schedule">View Calendar <ArrowRight size={14}/></Link></div><div className="cal-nav"><button className="icon-btn" onClick={()=>shift(-1)}><ChevronLeft size={18}/></button><strong>{cursor.toLocaleString("default",{month:"long"})} {year}</strong><button className="icon-btn" onClick={()=>shift(1)}><ChevronRight size={18}/></button></div><div className="cal-grid">{DAYS.map(d=><div key={d} className="cal-head">{d}</div>)}{cells.map((d,i)=><div key={i} className="cal-cell">{d&&<span className={isToday(d)?"today":""}>{d}</span>}{d&&dots[d]>0&&<i className="dot" style={{background:"#5b3fd6"}} title={`${dots[d]} scheduled item(s)`}/>}</div>)}</div></section>;
}