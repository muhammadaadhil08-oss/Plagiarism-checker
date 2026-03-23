from ai_detector import analyze_text
import json

doc1 = """During the pandemic, many schools and colleges started using online classes. At first, students found it difficult because they were not used to studying through a screen. Some students also had internet problems, which made learning harder. However, after some time people slowly adjusted to the new system. Teachers started using presentations and videos to explain lessons more clearly. Students also learned how to submit assignments and attend classes through different platforms. Even though online learning has many advantages, many students still prefer classroom learning because they can interact with teachers and friends directly."""

doc2 = """Online education became widely adopted during the pandemic as educational institutions shifted from traditional classrooms to digital platforms. This transition initially presented challenges for students who were unfamiliar with virtual learning environments. Over time, both teachers and students adapted to the system by utilizing various online tools such as video conferencing, digital presentations, and learning management systems. These technologies allowed educators to deliver lessons effectively and maintain academic continuity. Despite its flexibility and accessibility, many students still favor physical classrooms because they offer better face-to-face interaction and collaborative learning experiences."""

print("--- DOC 1 (Human-like) ---")
res1 = analyze_text(doc1)
for m, score in res1["metrics"].items():
    print(f"  {m}: {score}")
print(f"TOTAL AI PROB: {res1['ai_probability']}%")

print("\n--- DOC 2 (AI-like) ---")
res2 = analyze_text(doc2)
for m, score in res2["metrics"].items():
    print(f"  {m}: {score}")
print(f"TOTAL AI PROB: {res2['ai_probability']}%")
