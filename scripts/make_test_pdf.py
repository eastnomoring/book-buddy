"""生成一个用于端到端冒烟测试的英文概率论小册子 PDF"""
import fitz  # PyMuPDF

CONTENT = [
    ("Chapter 1: Sample Spaces and Probability",
     "A sample space Omega is the set of all possible outcomes of an experiment. "
     "An event is a subset of the sample space. The probability of an event A, "
     "denoted P(A), is a number between 0 and 1 that measures the likelihood of A. "
     "For a finite sample space with equally likely outcomes, P(A) equals the "
     "number of outcomes in A divided by the total number of outcomes. "
     "The axioms of probability require that P(Omega) = 1, P(A) >= 0 for every "
     "event A, and that probabilities add over disjoint events. " * 4),
    ("Chapter 2: Conditional Probability",
     "The conditional probability of A given B is defined as P(A|B) = P(A and B) / P(B), "
     "provided P(B) > 0. The law of total probability states that if B1, B2, ..., Bn "
     "partition the sample space, then P(A) = sum over i of P(A|Bi) P(Bi). "
     "Bayes theorem reverses the conditioning: P(Bi|A) = P(A|Bi) P(Bi) / P(A). "
     "Two events A and B are independent when P(A and B) = P(A) P(B). " * 4),
    ("Chapter 3: Expectation and the Tower Property",
     "The expected value of a discrete random variable X is E[X] = sum of x P(X = x). "
     "Expectation is linear: E[aX + bY] = a E[X] + b E[Y], even when X and Y are "
     "dependent. Conditional expectation E[X|Y] is a random variable that equals "
     "E[X|Y = y] whenever Y = y. The tower property (law of total expectation) says "
     "E[E[X|Y]] = E[X]. Intuitively, averaging conditional averages gives the "
     "overall average. The law of large numbers states that the sample mean of "
     "independent identically distributed random variables converges to E[X]. " * 4),
]


def main():
    doc = fitz.open()
    for chapter, body in CONTENT:
        for page_no in range(3):  # 每章 3 页
            page = doc.new_page()
            text = chapter if page_no == 0 else ""
            text = (text + "\n\n" + body).strip()
            page.insert_text((72, 72), text, fontsize=11, fontname="helv")
    doc.save("data/books/test_probability.pdf")
    doc.close()
    print("OK: data/books/test_probability.pdf")


if __name__ == "__main__":
    main()
