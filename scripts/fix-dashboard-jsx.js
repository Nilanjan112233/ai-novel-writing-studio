const fs = require('fs')
const p = 'frontend/app/dashboard/page.tsx'
let t = fs.readFileSync(p, 'utf8')
const closeDiv = '</' + 'motion-safe-flow'.replace('motion-safe-flow', 'div')

const rules = [
  ['<h2 className="text-3xl font-bold">{selectedProject.title}' + closeDiv, '<h2 className="text-3xl font-bold">{selectedProject.title}</h2>'],
  ['{selectedProject.premise || selectedProject.idea_dump}\n                      ' + closeDiv, '{selectedProject.premise || selectedProject.idea_dump}\n                      </p>'],
  ['{currentRun.current_agent ? ` · Agent: ${currentRun.current_agent}` : null}\n                    ' + closeDiv, '{currentRun.current_agent ? ` · Agent: ${currentRun.current_agent}` : null}\n                    </p>'],
  ['Workflow Runs\n                    ' + closeDiv, 'Workflow Runs\n                    </h3>'],
  ['<p>No outputs yet' + closeDiv, '<p>No outputs yet</p>'],
  ['<p>No questions generated.' + closeDiv, '<p>No questions generated.</p>'],
  ['Outline not available yet.' + closeDiv, 'Outline not available yet.</p>'],
  ['<h3 className="text-2xl font-semibold mb-2">No Project Selected' + closeDiv, '<h3 className="text-2xl font-semibold mb-2">No Project Selected</h3>'],
  ['Create or select a project to get started.' + closeDiv, 'Create or select a project to get started.</p>'],
  ['<p className="font-semibold mb-2">{output.agent_name}' + closeDiv, '<p className="font-semibold mb-2">{output.agent_name}</p>'],
  ['<p className="font-semibold mb-2">{question.text}' + closeDiv, '<p className="font-semibold mb-2">{question.text}</p>'],
  ['<p className="text-sm text-green-600">Answered: {question.answer}' + closeDiv, '<p className="text-sm text-green-600">Answered: {question.answer}</p>'],
  ['<p className="text-sm" data-testid="outline-premise">{outline!.premise}' + closeDiv, '<p className="text-sm" data-testid="outline-premise">{outline!.premise}</p>'],
  ['<p className="text-sm">{selectedProject.title}' + closeDiv, '<p className="text-sm">{selectedProject.title}</p>'],
]

for (const [from, to] of rules) {
  t = t.split(from).join(to)
}

const h4Close = closeDiv
t = t.replace(new RegExp('<h4 className="font-semibold mb-2">([^<]*)' + h4Close.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '<h4 className="font-semibold mb-2">$1</h4>')
t = t.replace(new RegExp('<p className="font-medium">([^<]*)' + h4Close.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '<p className="font-medium">$1</p>')
t = t.replace(new RegExp('<p className="text-sm text-muted-foreground">([^<]*)' + h4Close.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '<p className="text-sm text-muted-foreground">$1</p>')

fs.writeFileSync(p, t)
console.log('fixed')
