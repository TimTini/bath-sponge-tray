# Khay bông tắm — Autodesk Fusion

`BathSpongeTray/BathSpongeTray.py` tạo một document mới với solid BRep, sketch ràng buộc đầy đủ và timeline parametric. Không cần cài thư viện Python ngoài Fusion. File `.manifest` phải nằm cùng thư mục và cùng tên với file `.py`.

## Chạy

1. Tải cả thư mục `BathSpongeTray` (gồm `.py` và `.manifest`).
2. Trong Fusion mở **Utilities > Add-Ins > Scripts and Add-Ins**, chọn tab **Scripts**, bấm **+** và chọn thư mục `BathSpongeTray`.
3. Chọn script **BathSpongeTray**, bấm **Run**. Mỗi lần chạy tạo một document mới; document đang làm không bị sửa.
4. Mở **Modify > Change Parameters** để sửa các User Parameters. Mô hình và pattern cập nhật qua công thức trong timeline; không cần chạy lại Python khi đổi kích thước.

Quy trình thêm/chạy script theo [hướng dẫn Autodesk](https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-MANAGE-SCRIPTS-ADD-INS.htm).

Mặc định `HOOK_COUNT = 1` ở đầu file Python. Để tạo bản hai lỗ, đổi dòng này thành `HOOK_COUNT = 2`, rồi chạy script để tạo document riêng. Đây là lựa chọn cấu trúc lúc tạo; không phải một tham số đổi số lỗ trong Change Parameters. Hai bản đều có toàn bộ kích thước điều khiển bằng User Parameters.

## Tham số

Đơn vị hiển thị là **mm**; tên biến tiếng Anh, phần mô tả có tiếng Việt. Giá trị ban đầu đồng bộ với bản SCAD.

| Tham số | Mặc định | Ý nghĩa |
|---|---:|---|
| `length`, `width`, `height` | 100, 70, 30 | Dài, ngang, cao thân |
| `wall`, `floor_thickness` | 3, 3 | Dày thành/tai, dày đáy |
| `corner_radius` | 8 | Bo góc ngoài; góc lòng tự tính bằng `corner_radius - wall` |
| `drain_diameter`, `drain_pitch` | 6, 12 | Đường kính và bước tâm lỗ đáy |
| `drain_edge_margin` | 10 | Lề tối thiểu từ mép ngoài đến tâm lỗ đáy |
| `hook_diameter` | 10 | Đường kính lỗ móc |
| `hook_spacing`, `hook_height` | 60, 20 | Khoảng tâm và cao tâm móc trong bản hai lỗ |
| `ear_width`, `ear_rise` | 30, 17 | Rộng tai và chiều cao tai trên miệng trong bản một lỗ |
| `ear_root_radius` | 3 | Fillet lõm nối tai với miệng khay |

Giữ công thức của các tham số tự tính:

```text
drain_columns = floor((length - 2 * drain_edge_margin) / drain_pitch) + 1
drain_rows = floor((width - 2 * drain_edge_margin) / drain_pitch) + 1
drain_start_x = (length - (drain_columns - 1) * drain_pitch) / 2
drain_start_y = (width - (drain_rows - 1) * drain_pitch) / 2
ear_hole_height = ear_rise / 2
```

Lỗ móc đơn luôn ở `X = length / 2`, `Z = height + ear_hole_height`; thành sau luôn theo `width`, độ dày tai theo `wall`. Hai lỗ móc luôn ở `X = (length ± hook_spacing) / 2`, cao `hook_height`. Bo đỉnh tai R5 giữ như SCAD.

Ví dụ đổi khay thành 160 × 100 mm: lưới đổi từ 7 × 5 thành 12 × 7, tâm lỗ đầu ở (14, 14) mm. Đổi `ear_rise` thành 20 mm và giữ `height = 30 mm`: tâm lỗ móc cao 40 mm, giữa phần tai nhô lên.

“Tự tính” áp dụng cho các vị trí, số lượng và kích thước phụ thuộc. Đường kính lỗ, độ dày, bước lỗ và bán kính bo vẫn chỉnh độc lập; không tự phóng to tất cả theo tỷ lệ khay.

## Giới hạn hình học và kiểm chứng

- Dài/ngang phải lớn hơn `2 * corner_radius`; `corner_radius > wall`; `height > floor_thickness`.
- `drain_pitch >= drain_diameter + 3 mm`; `drain_edge_margin >= max(corner_radius, wall + drain_diameter / 2 + 3 mm)`; mỗi chiều có ít nhất một lỗ.
- Bản một lỗ: `height > 5 mm`, `ear_width >= hook_diameter + 10 mm`, `ear_rise >= hook_diameter + 6 mm`; `ear_root_radius <= ear_rise / 2`; `ear_width + 2 * ear_root_radius <= length - 2 * corner_radius`.
- Bản hai lỗ: `hook_spacing > hook_diameter`; `(length - hook_spacing - hook_diameter) / 2 >= corner_radius + 3 mm`; tâm lỗ cách đáy lòng và miệng khay ít nhất `hook_diameter / 2 + 3 mm`.

Script kiểm tra các giới hạn trên trước khi dựng mô hình. Sau khi sửa trong Change Parameters, cần giữ các giới hạn này; script không chạy nền để chặn mọi tổ hợp không hợp lệ. Fusion có thể báo lỗi feature nếu kích thước làm fillet, thành hoặc lỗ không còn dựng được.

`VERIFY_VARIANTS = True` ở đầu Python bật bảy ca đổi kích thước trong Fusion rồi phục hồi giá trị gốc, gồm cả lưới 1 × 1. Kiểm tra gồm compute timeline, trạng thái feature, sketch đủ ràng buộc, một solid, kích thước bao, vị trí/đường kính sketch lỗ và số lượng pattern. Chạy riêng cho `HOOK_COUNT = 1` và `2`. Đây không phải kiểm tra tải, in thật hoặc audit mặt cắt STL.

Kiểm tra độc lập với Fusion, chạy ở thư mục gốc repo:

```console
python -m unittest discover -s tests -v
```

**Trạng thái bàn giao:** đã kiểm tra công thức/giới hạn, đồng bộ mặc định với SCAD và cú pháp Python; đã đối chiếu API với tài liệu Autodesk và API cài trên máy. Chưa chạy dựng solid hoặc kiểm tra thay đổi tham số trong ứng dụng Fusion. Phần tự kiểm tra ở trên sẽ báo kết quả khi script được chạy trong Fusion.

Script và manifest được cung cấp trên GitHub. Không đưa `.py` vào bộ file MakerWorld vì MakerWorld đã từ chối định dạng này.
