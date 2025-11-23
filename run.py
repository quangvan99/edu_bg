"""
GiaoAn AI - Version 2.0
Hệ thống tạo giáo án thông minh với format động từ file mẫu
"""

import os
import re
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import pypandoc
from google import genai

os.environ['PYTHONIOENCODING'] = 'utf-8'
console = Console()

class Config:
    API_KEY = "AIzaSyDvfeKx6BT4JXL-CItT37bjP3mLmKzfxS0"
    MODEL = 'gemini-2.0-flash'
    OUTPUT_DIR = "results"
    FORMAT_FILE = "format/format.docx"

class AIClient:
    """Client wrapper cho Google Gemini API"""

    def __init__(self, api_key: str = Config.API_KEY, model: str = Config.MODEL):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_response(self, prompt: str) -> str:
        """Generate response từ Gemini API"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            console.print(f"[red]Lỗi API: {e}[/red]")
            return ""

class StructureParser:
    """Parse cấu trúc giáo án từ file format"""

    def __init__(self, format_file: str = Config.FORMAT_FILE):
        self.format_file = format_file
        self.structure = {}
        self.format_content = ""

    def parse(self):
        """Parse file format để trích xuất cấu trúc"""
        # Convert docx sang markdown
        md_file = self.format_file.replace('.docx', '_extracted.md')

        if not os.path.exists(md_file):
            try:
                pypandoc.convert_file(self.format_file, 'md', outputfile=md_file)
            except Exception as e:
                console.print(f"[red]Lỗi parse format: {e}[/red]")
                return {}

        # Đọc nội dung markdown
        with open(md_file, 'r', encoding='utf-8') as f:
            self.format_content = f.read()

        # Parse cấu trúc từ markdown
        self.structure = self._extract_structure(self.format_content)
        return self.structure

    def _extract_structure(self, content: str) -> dict:
        """Trích xuất cấu trúc từ markdown content"""
        lines = content.split('\n')

        # Bước 1: Tìm level thấp nhất (số # ít nhất) để biết cấu trúc
        min_level = 6
        for line in lines:
            match = re.match(r'^(#{1,6})\s+', line)
            if match:
                level = len(match.group(1))
                min_level = min(min_level, level)

        # Bước 2: Normalize - Nếu không có level 1, shift tất cả về level 1
        level_offset = min_level - 1

        structure = {
            'sections': [],
            'headers': {},
            'level1_title': None,
            'level_offset': level_offset  # Lưu offset để normalize khi xuất
        }

        current_section = None

        for line in lines:
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                raw_level = len(match.group(1))
                title = match.group(2).strip()

                # Normalize level
                level = raw_level - level_offset

                # Level 1: Tiêu đề chính (Nội dung bài giảng: ...)
                if level == 1:
                    structure['level1_title'] = title

                # Level 2: Section chính (Mục tiêu, Thiết bị, Tiến trình...)
                elif level == 2:
                    section = {
                        'title': title,
                        'level': level,
                        'subsections': []
                    }
                    structure['sections'].append(section)
                    current_section = section
                    structure['headers'][title] = section

                # Level 3: Subsection (Năng lực, Giáo viên, Hoạt động 1...)
                elif level == 3 and current_section:
                    subsection = {
                        'title': title,
                        'level': level,
                        'parts': []
                    }
                    current_section['subsections'].append(subsection)

                # Level 4: Parts (Năng lực chung, Mục tiêu, Nội dung...)
                elif level == 4 and current_section:
                    if current_section['subsections']:
                        part = {
                            'title': title,
                            'level': level
                        }
                        current_section['subsections'][-1]['parts'].append(part)

        return structure

    def get_sections(self):
        """Lấy danh sách các section chính"""
        return [s['title'] for s in self.structure.get('sections', [])]

    def get_subsections(self, section_title: str):
        """Lấy danh sách subsection của một section"""
        section = self.structure['headers'].get(section_title)
        if section:
            return [s['title'] for s in section.get('subsections', [])]
        return []

    def get_all_units_by_level(self, target_level: int = 3):
        """
        Lấy tất cả các unit cần tạo theo target_level
        target_level = 3: Tạo các ### (Năng lực, Phẩm chất, Hoạt động 1, ...)
        target_level = 4: Tạo các #### (Năng lực chung, Năng lực môn học, Mục tiêu, ...)
        """
        units = []

        for section in self.structure.get('sections', []):
            # Level 2: Section chính
            section_title = section['title']

            if target_level == 2:
                # Tạo cả section
                units.append({
                    'type': 'section',
                    'level': 2,
                    'title': section_title,
                    'parent': None,
                    'full_path': section_title
                })

            elif target_level == 3:
                # Tạo từng subsection (level 3)
                for subsection in section.get('subsections', []):
                    units.append({
                        'type': 'subsection',
                        'level': 3,
                        'title': subsection['title'],
                        'parent': section_title,
                        'full_path': f"{section_title} > {subsection['title']}"
                    })

            elif target_level >= 4:
                # Tạo từng part (level 4+)
                for subsection in section.get('subsections', []):
                    for part in subsection.get('parts', []):
                        units.append({
                            'type': 'part',
                            'level': 4,
                            'title': part['title'],
                            'parent': f"{section_title} > {subsection['title']}",
                            'full_path': f"{section_title} > {subsection['title']} > {part['title']}"
                        })

        return units

class DynamicPromptGenerator:
    """Tạo prompt động dựa trên cấu trúc"""

    SYSTEM_BASE = """
    Bạn là trợ lí xuất sắc của giáo viên về công việc hỗ trợ xây dựng giáo án bài giảng.
    Hãy đưa ra những thông tin hữu ích và chính xác để xây dựng bài giảng mà người dùng yêu cầu.
    """

    @staticmethod
    def generate_create_prompt(section_info: dict, example_content: str = "") -> str:
        """Tạo prompt cho việc tạo mới section"""
        section_title = section_info.get('title', 'Nội dung')
        structure = section_info.get('structure', '')

        prompt = f"""
Nhiệm vụ: Tạo mới **{section_title}** dưới dạng Markdown, theo cấu trúc bắt buộc:

{structure}

**Yêu cầu**:
- Nội dung phải cụ thể, rõ ràng, dễ hiểu.
- Bám sát đối tượng học sinh và nội dung bài giảng.
- Đầu ra chỉ bao gồm phần **{section_title}** theo đúng cấu trúc yêu cầu, không thêm bất kỳ thông tin nào khác.
- **Định dạng công thức toán học**:
  - Sử dụng dấu đô la đơn (`$`) cho công thức nội tuyến. Ví dụ: `$y = ax + b$`.
  - Sử dụng hai dấu đô la (`$$`) trên dòng riêng cho công thức độc lập. Ví dụ:
    `$$
    \\Delta = b^2 - 4ac
    $$`
"""

        if example_content:
            prompt += f"\n**Ví dụ tham khảo**:\n{example_content}\n"

        prompt += "\n** Đầu vào để sinh nội dung phù hợp: **\n"

        return prompt

    @staticmethod
    def generate_update_prompt(section_info: dict) -> str:
        """Tạo prompt cho việc cập nhật section"""
        section_title = section_info.get('title', 'Nội dung')
        structure = section_info.get('structure', '')

        prompt = f"""
Nhiệm vụ: Cập nhật **{section_title}** dưới dạng Markdown, theo cấu trúc bắt buộc:

{structure}

**Yêu cầu**:
- Cập nhật sát với yêu cầu người dùng bổ sung.
- Giữ đúng cấu trúc, không thêm phần thuyết minh ngoài.
- **Định dạng công thức toán học**:
  - Sử dụng dấu đô la đơn (`$`) cho công thức nội tuyến.
  - Sử dụng hai dấu đô la (`$$`) trên dòng riêng cho công thức độc lập.

**Các yêu cầu người dùng cần bổ sung:**
"""
        return prompt

class GiaoAnGenerator:
    """Class chính để tạo giáo án động"""

    def __init__(self):
        self.ai_client = AIClient()
        self.structure_parser = StructureParser()
        self.prompt_gen = DynamicPromptGenerator()

        self.sections_data = {}
        self.structure = {}
        self.noi_dung_bai_giang = ""
        self.detail_level = 3  # Mặc định tạo đến level 3

        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

    def initialize(self):
        """Khởi tạo và parse cấu trúc"""
        self.structure = self.structure_parser.parse()

        if not self.structure:
            console.print("[yellow]Không tìm thấy file format, sử dụng cấu trúc mặc định[/yellow]")
            return False
        return True

    def show_outline(self):
        """Hiển thị outline từ format để xác nhận"""
        console.print("\n" + "="*60, style="bold cyan")
        console.print("OUTLINE CẤU TRÚC GIÁO ÁN", style="bold cyan")
        console.print("="*60 + "\n", style="bold cyan")

        # Hiển thị Level 1 title
        level1 = self.structure.get('level1_title', 'Nội dung bài giảng')
        console.print(f"# {level1}", style="bold green")

        # Hiển thị các sections
        sections = self.structure.get('sections', [])
        for i, section in enumerate(sections, 1):
            console.print(f"\n{i}. ## {section['title']}", style="bold blue")

            # Hiển thị subsections
            for subsection in section.get('subsections', []):
                console.print(f"   - ### {subsection['title']}", style="yellow")

                # Hiển thị parts (nếu có)
                for part in subsection.get('parts', [])[:3]:  # Chỉ show 3 parts đầu
                    console.print(f"      • #### {part['title']}", style="dim")

        console.print("\n" + "="*60 + "\n", style="bold cyan")

    def confirm_outline(self) -> bool:
        """Xác nhận outline với user"""
        self.show_outline()

        console.print("Cấu trúc trên được parse từ file format.docx", style="italic")

        # Thông tin hướng dẫn
        info = """
[cyan]Tùy chọn:[/cyan]
  [green]y[/green] = Tiếp tục tạo giáo án với outline này
  [red]n[/red] = Hủy (sửa file format.docx rồi chạy lại)
  [yellow]s[/yellow] = Xem nội dung file format.docx
  [blue]e[/blue] = Chỉnh sửa sections (bỏ qua sections không cần)
  [magenta]l[/magenta] = Chọn level chi tiết (mặc định: level 3)
"""
        console.print(info)

        while True:
            choice = input("Lựa chọn của bạn: ").lower().strip()

            if choice in ['y', 'yes', 'có', '']:
                return True
            elif choice in ['n', 'no', 'không']:
                console.print("Đã hủy. Vui lòng kiểm tra lại file format.docx", style="yellow")
                return False
            elif choice in ['s', 'show']:
                self._show_format_preview()
            elif choice in ['e', 'edit']:
                self._edit_sections()
                self.show_outline()
                console.print(info)
            elif choice in ['l', 'level']:
                self._select_detail_level()
                console.print(info)
            else:
                console.print("Vui lòng nhập y/n/s/e/l", style="red")

    def _select_detail_level(self):
        """Cho phép user chọn level chi tiết"""
        console.print("\n[bold]Chọn mức độ chi tiết khi tạo giáo án:[/bold]")
        console.print("  3 = Level 3 (### - mặc định, ví dụ: Năng lực, Phẩm chất)")
        console.print("  4 = Level 4 (#### - chi tiết hơn, ví dụ: Năng lực chung, Năng lực môn học)")
        console.print("  5 = Level 5 (##### - rất chi tiết)")

        level_input = input("\nNhập level (3/4/5): ").strip()

        try:
            level = int(level_input)
            if level in [3, 4, 5]:
                self.detail_level = level
                console.print(f"Đã chọn level {level}", style="green")
            else:
                console.print("Level không hợp lệ. Giữ mặc định level 3", style="yellow")
        except ValueError:
            console.print("Định dạng không hợp lệ. Giữ mặc định level 3", style="yellow")

    def _edit_sections(self):
        """Cho phép user bỏ qua các sections không cần"""
        sections = self.structure.get('sections', [])

        console.print("\n[bold]Chọn sections cần tạo:[/bold]")
        console.print("(Nhập số sections cần BỎ QUA, cách nhau bằng dấu phẩy. VD: 1,3)")
        console.print("(Để trống = giữ tất cả)\n")

        for i, section in enumerate(sections, 1):
            console.print(f"  {i}. {section['title']}", style="cyan")

        skip_input = input("\nCác sections cần bỏ qua: ").strip()

        if not skip_input:
            console.print("Giữ tất cả sections", style="green")
            return

        try:
            skip_indices = [int(x.strip()) - 1 for x in skip_input.split(',')]
            skip_indices = [i for i in skip_indices if 0 <= i < len(sections)]

            # Lọc bỏ sections
            filtered_sections = [s for i, s in enumerate(sections) if i not in skip_indices]

            self.structure['sections'] = filtered_sections
            self.structure['headers'] = {s['title']: s for s in filtered_sections}

            console.print(f"\nĐã bỏ qua {len(skip_indices)} sections", style="green")

        except ValueError:
            console.print("Định dạng không hợp lệ. Giữ tất cả sections", style="yellow")

    def _show_format_preview(self):
        """Hiển thị preview nội dung format file"""
        console.print("\n" + "="*60, style="dim")
        console.print("PREVIEW FORMAT FILE (50 dòng đầu)", style="bold dim")
        console.print("="*60 + "\n", style="dim")

        lines = self.structure_parser.format_content.split('\n')[:50]
        preview = '\n'.join(lines)

        md = Markdown(preview, code_theme="monokai")
        console.print(md)
        console.print("\n... (còn tiếp)\n", style="dim")
        console.print("="*60 + "\n", style="dim")

    def extract_markdown(self, raw_str: str) -> str:
        """Trích xuất nội dung Markdown sạch"""
        match = re.search(r"```(?:markdown)?\s*\n(.*?)```", raw_str, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return raw_str.strip()

    def show_markdown(self, md_str: str, title: str = ""):
        """Hiển thị nội dung Markdown"""
        if title:
            console.print(Panel(title, border_style="blue"))

        md = Markdown(md_str, code_theme="monokai", hyperlinks=True)
        console.print(md, soft_wrap=True)
        console.print()

    def get_user_input(self, prompt: str, allow_empty: bool = False) -> str:
        """Lấy input từ người dùng"""
        while True:
            try:
                user_input = input(f"{prompt} ")
                if user_input.strip() or allow_empty:
                    return user_input.strip()
                console.print("Vui lòng nhập nội dung!", style="red")
            except (UnicodeDecodeError, KeyboardInterrupt):
                return ""

    def ask_to_continue(self, section_name: str) -> bool:
        """Hỏi người dùng có muốn chỉnh sửa không"""
        choice = input(f"Bạn có muốn chỉnh sửa {section_name}? (y/n): ").lower()
        return choice in ['y', 'yes', 'có']

    def process_unit(self, unit: dict, context: str = ""):
        """Xử lý một unit bất kỳ (section/subsection/part)"""
        unit_title = unit['full_path']
        console.print(f"\n=== Tạo: {unit_title} ===", style="bold blue")

        # Lấy cấu trúc từ format
        unit_structure = self._extract_unit_structure(unit)
        example_content = self._extract_unit_example(unit)

        # Tạo prompt
        unit_info = {
            'title': unit_title,
            'structure': unit_structure,
            'level': unit['level']
        }

        prompt_create = self.prompt_gen.generate_create_prompt(unit_info, example_content)

        # Gọi AI để tạo nội dung
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task(f"Đang tạo {unit['title']}...", total=None)
            full_prompt = self.prompt_gen.SYSTEM_BASE + "\n" + prompt_create + "\n" + context
            response = self.ai_client.generate_response(full_prompt)
            progress.update(task, description="Hoàn thành!")

        content = self.extract_markdown(response)
        self.show_markdown(content, f"{unit['title']} đã tạo")

        # Cho phép cập nhật
        while self.ask_to_continue(unit['title']):
            update_input = self.get_user_input(f"Nhập thông tin cập nhật cho {unit['title']}:")

            prompt_update = self.prompt_gen.generate_update_prompt(unit_info)

            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task(f"Đang cập nhật {unit['title']}...", total=None)
                full_prompt = self.prompt_gen.SYSTEM_BASE + "\n" + prompt_update + "\n" + update_input + "\n\nNội dung hiện tại:\n" + content
                response = self.ai_client.generate_response(full_prompt)
                progress.update(task, description="Hoàn thành!")

            content = self.extract_markdown(response)
            self.show_markdown(content, f"{unit['title']} đã cập nhật")

        # Lưu vào dict theo full_path
        self.sections_data[unit_title] = content
        filename = self._to_filename(unit['title'])
        self.save_file(filename, content)

        return content

    def _extract_unit_structure(self, unit: dict) -> str:
        """Trích xuất cấu trúc của unit từ format"""
        if unit['type'] == 'section':
            return self._extract_section_structure(unit['title'])
        elif unit['type'] == 'subsection':
            return self._extract_subsection_structure(unit['parent'], unit['title'])
        elif unit['type'] == 'part':
            parts = unit['parent'].split(' > ')
            if len(parts) >= 2:
                return self._extract_part_structure(parts[0], parts[1], unit['title'])
        return ""

    def _extract_unit_example(self, unit: dict) -> str:
        """Trích xuất ví dụ của unit từ format"""
        if unit['type'] == 'section':
            return self._extract_section_example(unit['title'])
        elif unit['type'] == 'subsection':
            return self._extract_subsection_example(unit['parent'], unit['title'])
        elif unit['type'] == 'part':
            parts = unit['parent'].split(' > ')
            if len(parts) >= 2:
                return self._extract_part_example(parts[0], parts[1], unit['title'])
        return ""

    def _extract_section_structure(self, section_title: str) -> str:
        """Trích xuất cấu trúc của section từ format"""
        content = self.structure_parser.format_content

        # Tìm section trong format
        pattern = rf"## {re.escape(section_title)}(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            section_content = match.group(1).strip()
            # Lấy tất cả các headers và một chút nội dung mẫu
            lines = []
            in_table = False
            for line in section_content.split('\n'):
                # Lấy headers
                if re.match(r'^#{1,4}\s', line):
                    lines.append(line)
                # Lấy phần đầu của table (ví dụ cho Tổ chức thực hiện)
                elif '|' in line and not in_table:
                    lines.append(line)
                    in_table = True
                elif in_table and '|' in line:
                    lines.append(line)
                    if '---' in line:
                        lines.append('| (mô tả chi tiết) | (nội dung cụ thể) |')
                        in_table = False
                # Lấy bullet list đầu tiên làm mẫu
                elif re.match(r'^-\s', line) and len(lines) > 0:
                    if lines[-1].startswith('#'):
                        lines.append('- (liệt kê rõ ràng)')

            return '\n'.join(lines)

        return ""

    def _extract_section_example(self, section_title: str) -> str:
        """Trích xuất ví dụ của section từ format (giới hạn)"""
        content = self.structure_parser.format_content

        pattern = rf"## {re.escape(section_title)}(.*?)(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            return match.group(1).strip()[:1000]

        return ""

    def _extract_subsection_structure(self, section_title: str, subsection_title: str) -> str:
        """Trích xuất cấu trúc của subsection (level 3)"""
        content = self.structure_parser.format_content

        # Tìm section trước
        section_pattern = rf"## {re.escape(section_title)}(.*?)(?=\n## |\Z)"
        section_match = re.search(section_pattern, content, re.DOTALL)

        if not section_match:
            return ""

        section_content = section_match.group(1)

        # Tìm subsection trong section
        subsection_pattern = rf"### {re.escape(subsection_title)}(.*?)(?=\n### |\n## |\Z)"
        subsection_match = re.search(subsection_pattern, section_content, re.DOTALL)

        if subsection_match:
            subsection_content = subsection_match.group(1).strip()
            # Lấy structure
            lines = []
            for line in subsection_content.split('\n')[:20]:
                if re.match(r'^#{1,5}\s', line) or '|' in line or re.match(r'^-\s', line):
                    lines.append(line)
            return f"### {subsection_title}\n" + '\n'.join(lines)

        return f"### {subsection_title}"

    def _extract_subsection_example(self, section_title: str, subsection_title: str) -> str:
        """Trích xuất ví dụ của subsection"""
        content = self.structure_parser.format_content

        section_pattern = rf"## {re.escape(section_title)}(.*?)(?=\n## |\Z)"
        section_match = re.search(section_pattern, content, re.DOTALL)

        if not section_match:
            return ""

        section_content = section_match.group(1)

        subsection_pattern = rf"### {re.escape(subsection_title)}(.*?)(?=\n### |\n## |\Z)"
        subsection_match = re.search(subsection_pattern, section_content, re.DOTALL)

        if subsection_match:
            return subsection_match.group(1).strip()[:800]

        return ""

    def _extract_part_structure(self, section_title: str, subsection_title: str, part_title: str) -> str:
        """Trích xuất cấu trúc của part (level 4)"""
        content = self.structure_parser.format_content

        # Navigate: section -> subsection -> part
        section_pattern = rf"## {re.escape(section_title)}(.*?)(?=\n## |\Z)"
        section_match = re.search(section_pattern, content, re.DOTALL)

        if not section_match:
            return ""

        section_content = section_match.group(1)

        subsection_pattern = rf"### {re.escape(subsection_title)}(.*?)(?=\n### |\n## |\Z)"
        subsection_match = re.search(subsection_pattern, section_content, re.DOTALL)

        if not subsection_match:
            return ""

        subsection_content = subsection_match.group(1)

        part_pattern = rf"#### {re.escape(part_title)}(.*?)(?=\n#### |\n### |\n## |\Z)"
        part_match = re.search(part_pattern, subsection_content, re.DOTALL)

        if part_match:
            part_content = part_match.group(1).strip()
            lines = []
            for line in part_content.split('\n')[:15]:
                if re.match(r'^#{1,6}\s', line) or '|' in line or re.match(r'^-\s', line):
                    lines.append(line)
            return f"#### {part_title}\n" + '\n'.join(lines)

        return f"#### {part_title}"

    def _extract_part_example(self, section_title: str, subsection_title: str, part_title: str) -> str:
        """Trích xuất ví dụ của part"""
        content = self.structure_parser.format_content

        section_pattern = rf"## {re.escape(section_title)}(.*?)(?=\n## |\Z)"
        section_match = re.search(section_pattern, content, re.DOTALL)

        if not section_match:
            return ""

        section_content = section_match.group(1)

        subsection_pattern = rf"### {re.escape(subsection_title)}(.*?)(?=\n### |\n## |\Z)"
        subsection_match = re.search(subsection_pattern, section_content, re.DOTALL)

        if not subsection_match:
            return ""

        subsection_content = subsection_match.group(1)

        part_pattern = rf"#### {re.escape(part_title)}(.*?)(?=\n#### |\n### |\n## |\Z)"
        part_match = re.search(part_pattern, subsection_content, re.DOTALL)

        if part_match:
            return part_match.group(1).strip()[:500]

        return ""

    def _to_filename(self, section_title: str) -> str:
        """Chuyển section title thành filename"""
        filename = re.sub(r'[^\w\s-]', '', section_title.lower())
        filename = re.sub(r'[-\s]+', '_', filename)
        return filename + '.md'

    def save_file(self, filename: str, content: str):
        """Lưu file"""
        filepath = os.path.join(Config.OUTPUT_DIR, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            console.print(f"[red]Lỗi lưu file: {e}[/red]")

    def export_final(self, format_type: str = 'docx'):
        """Xuất file cuối cùng với đầy đủ format"""
        # Lấy template từ format gốc hoặc tạo mặc định
        level1_template = self.structure.get('level1_title')

        if level1_template:
            if ':' in level1_template:
                prefix = level1_template.split(':')[0]
                level1_title = f"{prefix}: {self.noi_dung_bai_giang}" if self.noi_dung_bai_giang else level1_template
            else:
                level1_title = self.noi_dung_bai_giang or level1_template
        else:
            level1_title = f"Nội dung bài giảng: {self.noi_dung_bai_giang}" if self.noi_dung_bai_giang else "Giáo án"

        # Ghép toàn bộ nội dung theo đúng format
        full_content = f"# {level1_title}\n\n"

        # Xây dựng lại cấu trúc hoàn chỉnh từ các units đã tạo
        sections = self.structure.get('sections', [])

        for section in sections:
            section_title = section['title']
            full_content += f"## {section_title}\n\n"

            # Lấy nội dung từ các units
            for subsection in section.get('subsections', []):
                subsection_title = subsection['title']
                subsection_path = f"{section_title} > {subsection_title}"

                # Nếu tạo theo level 3, lấy content từ subsection
                if subsection_path in self.sections_data:
                    content = self.sections_data[subsection_path]
                    if not content.startswith('###'):
                        content = f"### {subsection_title}\n\n{content}"
                    full_content += content + "\n\n"
                else:
                    # Nếu tạo theo level 4, ghép từ các parts
                    full_content += f"### {subsection_title}\n\n"

                    for part in subsection.get('parts', []):
                        part_title = part['title']
                        part_path = f"{section_title} > {subsection_title} > {part_title}"

                        if part_path in self.sections_data:
                            content = self.sections_data[part_path]
                            if not content.startswith('####'):
                                content = f"#### {part_title}\n\n{content}"
                            full_content += content + "\n\n"

        if format_type == 'md':
            filepath = os.path.join(Config.OUTPUT_DIR, 'giaoan.md')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_content)
            console.print(f"Đã xuất: {filepath}", style="green bold")

        elif format_type == 'docx':
            filepath = os.path.join(Config.OUTPUT_DIR, 'giaoan.docx')
            try:
                pypandoc.convert_text(
                    full_content,
                    'docx',
                    format='md',
                    outputfile=filepath,
                    extra_args=['--standalone', '--mathjax']
                )
                console.print(f"Đã xuất: {filepath}", style="green bold")
            except Exception as e:
                console.print(f"[red]Lỗi xuất Word: {e}[/red]")

    def run(self):
        """Chạy quy trình tạo giáo án"""
        console.print(Panel(
            Text("GIAOAN AI v2.0 - Hệ thống tạo giáo án động", style="bold blue"),
            border_style="blue"
        ))

        if not self.initialize():
            console.print("[red]Không thể khởi tạo cấu trúc[/red]")
            return

        try:
            # Bước 0: Xác nhận outline
            if not self.confirm_outline():
                return

            # Lấy danh sách units theo detail_level
            units = self.structure_parser.get_all_units_by_level(self.detail_level)

            if not units:
                console.print("[yellow]Không tìm thấy unit nào[/yellow]")
                return

            console.print(f"\n[cyan]Sẽ tạo {len(units)} mục (level {self.detail_level})[/cyan]\n")

            # Bước 1: Nhập nội dung bài giảng
            console.print("\n" + "="*60, style="bold green")
            console.print("BẮT ĐẦU TẠO GIÁO ÁN", style="bold green")
            console.print("="*60 + "\n", style="bold green")

            self.noi_dung_bai_giang = self.get_user_input("Nhập nội dung bài giảng:")
            context = f"Nội dung bài giảng: {self.noi_dung_bai_giang}"

            # Xử lý từng unit
            for i, unit in enumerate(units, 1):
                console.print(f"\nBƯỚC {i}/{len(units)}", style="bold yellow")
                self.process_unit(unit, context)

                # Cập nhật context cho unit tiếp theo
                context += f"\n\n{unit['full_path']}:\n{self.sections_data[unit['full_path']]}"

            # Xuất file
            choice = input("\nXuất file: 1.Word 2.Markdown 3.Cả hai 4.Bỏ qua: ").strip()

            if choice == '1':
                self.export_final('docx')
            elif choice == '2':
                self.export_final('md')
            elif choice == '3':
                self.export_final('docx')
                self.export_final('md')

            console.print("\nHoàn tất!", style="bold green")

        except KeyboardInterrupt:
            console.print("\nĐã hủy", style="yellow")
        except Exception as e:
            console.print(f"\n[red]Lỗi: {e}[/red]")

def main():
    generator = GiaoAnGenerator()
    generator.run()

if __name__ == "__main__":
    main()
