// frontend/src/pages/Tasks.jsx
import { useEffect, useState } from "react";
import { fmtShort } from "../utils";
import api, { errorMessage } from "../api";
const COLUMNS=[{id:"todo",title:"To do"},{id:"progress",title:"In progress"},{id:"done",title:"Done"}];
export default function Tasks({phase="Project tasks"}){
 const [tasks,setTasks]=useState([]);const [over,setOver]=useState(null);const [error,setError]=useState("");
 const load=()=>api.get("/tasks").then(({data})=>setTasks(data)).catch(e=>setError(errorMessage(e,"Could not load tasks.")));useEffect(()=>{load();},[]);
 const update=async(id,changes)=>{try{const {data}=await api.patch(`/tasks/${id}`,changes);setTasks(old=>old.map(t=>t.id===id?data:t));}catch(e){setError(errorMessage(e,"Could not update task."));}};
 const drop=async(e,status)=>{e.preventDefault();const id=Number(e.dataTransfer.getData("id"));const task=tasks.find(t=>t.id===id);setOver(null);if(task&&task.status!==status)await update(id,{status});};
 const add=async()=>{const title=window.prompt("Task title");if(!title?.trim())return;try{const {data}=await api.post("/tasks",{title:title.trim(),status:"todo",priority:"Medium",due:fmtShort(new Date().toISOString().slice(0,10))});setTasks(old=>[...old,data]);}catch(e){setError(errorMessage(e,"Could not add task."));}};
 const remove=async(id)=>{try{await api.delete(`/tasks/${id}`);setTasks(old=>old.filter(t=>t.id!==id));}catch(e){setError(errorMessage(e,"Could not delete task."));}};
 const done=tasks.filter(t=>t.status==="done").length;const pct=tasks.length?done/tasks.length*100:0;
 return <><div className="page-head"><div><h1>Tasks</h1><p className="sub">Track daily work by status. Tasks come from the generated plan.</p></div><button className="btn" onClick={add}>Add task</button></div>{error&&<p className="error">{error}</p>}<section className="card"><div className="phase"><strong>{phase}</strong><span>{done} of {tasks.length} done</span></div><div className="bar" style={{marginTop:16}}><i style={{width:`${pct}%`}}/></div></section><div className="board">{COLUMNS.map(c=><div key={c.id} className={`col ${over===c.id?"over":""}`} onDragOver={e=>{e.preventDefault();setOver(c.id);}} onDragLeave={()=>setOver(null)} onDrop={e=>drop(e,c.id)}><h3>{c.title}</h3>{tasks.filter(t=>t.status===c.id).map(t=><div key={t.id} className="task" draggable onDragStart={e=>e.dataTransfer.setData("id",String(t.id))}><p>{t.title}</p><div className="meta"><span className={`badge b-${String(t.priority).toLowerCase()}`}>{t.priority}</span><span>{t.due}</span></div><div style={{display:"flex",gap:8,marginTop:8}}><button className="btn soft" onClick={()=>update(t.id,{status:COLUMNS[(COLUMNS.findIndex(x=>x.id===t.status)+1)%COLUMNS.length].id})}>Move</button><button className="btn soft" onClick={()=>remove(t.id)}>Delete</button></div></div>)}</div>)}</div></>
}
