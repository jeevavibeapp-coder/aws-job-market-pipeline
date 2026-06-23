'use client'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

const skillData = [
  { skill: 'Python', jobs: 142 },
  { skill: 'SQL', jobs: 118 },
  { skill: 'AWS', jobs: 97 },
  { skill: 'Snowflake', jobs: 64 },
  { skill: 'Spark', jobs: 58 },
  { skill: 'Airflow', jobs: 45 },
  { skill: 'dbt', jobs: 38 },
]

const locationData = [
  { name: 'Bangalore', value: 38 },
  { name: 'Hyderabad', value: 24 },
  { name: 'Chennai', value: 18 },
  { name: 'Remote', value: 15 },
  { name: 'Mumbai', value: 5 },
]

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444']

export default function JobCharts() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Jobs by Top Skills</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={skillData} layout="vertical">
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="skill" width={70} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="jobs" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Jobs by Location</h3>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={locationData}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={90}
              dataKey="value"
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {locationData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
