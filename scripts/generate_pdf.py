from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_fill_color(255, 255, 255)
        self.rect(0, 0, 210, 297, style='F')
        
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(237, 28, 36) # AMD Red
        self.cell(0, 10, 'ROCmPort AI: Agentic Migration Suite', border=0, new_x='LMARGIN', new_y='NEXT', align='R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', border=0, new_x='LMARGIN', new_y='NEXT', align='C')

pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)

# Slide 1: Title
pdf.add_page()
pdf.ln(50)
pdf.set_font('Helvetica', 'B', 36)
pdf.set_text_color(0, 0, 0)
pdf.cell(0, 20, 'ROCmPort AI', border=0, new_x='LMARGIN', new_y='NEXT', align='C')
pdf.set_font('Helvetica', 'B', 16)
pdf.set_text_color(237, 28, 36)
pdf.cell(0, 10, 'CUDA-to-ROCm Migration powered by Qwen', border=0, new_x='LMARGIN', new_y='NEXT', align='C')
pdf.ln(15)
pdf.set_font('Helvetica', '', 14)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 10, 'Built for the AMD Developer Hackathon', border=0, new_x='LMARGIN', new_y='NEXT', align='C')

# Slide 2: The Problem
pdf.add_page()
pdf.set_font('Helvetica', 'B', 20)
pdf.set_text_color(237, 28, 36)
pdf.cell(0, 15, '1. The Problem', border=0, new_x='LMARGIN', new_y='NEXT', align='L')
pdf.set_font('Helvetica', '', 14)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(0, 8, 'Millions of lines of legacy AI code are locked into CUDA.\n\nManually porting PyTorch code to ROCm is tedious, error-prone, and acts as a massive bottleneck for enterprises adopting AMD hardware.')
pdf.ln(10)
pdf.set_font('Helvetica', 'B', 16)
pdf.cell(0, 10, 'The Goal:', border=0, new_x='LMARGIN', new_y='NEXT', align='L')
pdf.set_font('Helvetica', '', 14)
pdf.multi_cell(0, 8, 'Drop the switching cost to AMD infrastructure to ZERO using open-source AI agents.')

# Slide 3: Architecture Diagram (ASCII)
pdf.add_page()
pdf.set_font('Helvetica', 'B', 20)
pdf.set_text_color(237, 28, 36)
pdf.cell(0, 15, '2. System Architecture', border=0, new_x='LMARGIN', new_y='NEXT', align='L')
pdf.set_font('Courier', '', 10)
pdf.set_text_color(0, 0, 0)

ascii_diagram = """
                    [ User Repository ]
                              |
                              v
                      [ Gradio UI ]
                              |
                              v
                       [ Pipeline ]
                              |
            +-----------------+-----------------+
     (Agentic Workflow)                (Deterministic Fallback)
            |                                   |
   [ CUDA Auditor ]                    [ Scanner ]
            |                                   |
   [ ROCm Engineer ]                   [ Patcher ]
            |                                   |
   [ Report Writer ]                   [ Artifacts ]
            |                                   |
  (Qwen3 on MI300X)                             |
            |                                   |
            +-----------------+-----------------+
                              v
               [ Final Migration Package ]
"""
pdf.set_fill_color(240, 240, 240)
pdf.multi_cell(0, 5, ascii_diagram, border=1, align='C', fill=True)

# Slide 4: Business Value & Solution
pdf.add_page()
pdf.set_font('Helvetica', 'B', 20)
pdf.set_text_color(237, 28, 36)
pdf.cell(0, 15, '3. Business Value & Implementation', border=0, new_x='LMARGIN', new_y='NEXT', align='L')
pdf.set_font('Helvetica', '', 14)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(0, 8, 'ROCmPort AI completely automates the migration process using a 3-agent CrewAI pipeline:\n\n- CUDA Auditor: Scans ASTs for blocking hardware-specific code.\n- ROCm Engineer: Drafts the unified ROCm patch for PyTorch.\n- Report Writer: Packages the diff alongside a generated Dockerfile and Runbook.\n\nBusiness Impact:\nSaves hundreds of developer hours per repository, allowing immediate utilization of high-performance AMD hardware without manual rewrites.')

# Slide 5: Hardware Benchmarks
pdf.add_page()
pdf.set_font('Helvetica', 'B', 20)
pdf.set_text_color(237, 28, 36)
pdf.cell(0, 15, '4. Hardware Proof (AMD MI300X)', border=0, new_x='LMARGIN', new_y='NEXT', align='L')
pdf.set_font('Helvetica', '', 14)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(0, 8, 'We deployed the agent-generated patch directly onto the AMD Developer Cloud.')
pdf.ln(5)
benchmark_text = """
Hardware: AMD Instinct MI300X (192 GB HBM3)
ROCm: ROCm 7.0 (via Quick Start PyTorch container)
Model: Qwen/Qwen2.5-0.5B-Instruct
Throughput tokens/sec: 67.7
P50 latency ms: 1884.49
Peak VRAM GB: 2.05
"""
pdf.set_font('Courier', '', 12)
pdf.set_fill_color(240, 240, 240)
pdf.multi_cell(0, 7, benchmark_text, border=1, align='L', fill=True)
pdf.ln(5)
pdf.set_font('Helvetica', 'I', 12)
pdf.multi_cell(0, 8, 'Result: Verified successful migration! Original PyTorch code was executed natively on AMD MI300X using the ROCm software stack.')

# Slide 6: Links
pdf.add_page()
pdf.set_font('Helvetica', 'B', 20)
pdf.set_text_color(237, 28, 36)
pdf.cell(0, 15, '5. Live Deployment', border=0, new_x='LMARGIN', new_y='NEXT', align='L')
pdf.set_font('Helvetica', '', 14)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(0, 10, 'GitHub Repository:\nhttps://github.com/nawangdorjay/rocmport-ai\n\nHugging Face Demo:\nhttps://huggingface.co/spaces/Nawangdorjay/rocmport-ai\n\nYouTube Pitch:\nhttps://youtu.be/3CDWDIOEwh0')

pdf.output('ROCmPort_AI_Presentation.pdf')
