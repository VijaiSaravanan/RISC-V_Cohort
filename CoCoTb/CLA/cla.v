module cla(
    input  wire [3:0] a,     // 4-bit input A
    input  wire [3:0] b,     // 4-bit input B
    input  wire       cin,   // Carry-in
    output wire [3:0] sum,   // 4-bit Sum
    output wire       cout   // Carry-out
);

    wire [3:0] G;  // Generate
    wire [3:0] P;  // Propagate
    wire [3:1] C;  // Internal carries

    assign G = a & b;
    assign P = a ^ b;

    assign C[1] = G[0] | (P[0] & cin);
    assign C[2] = G[1] | (P[1] & C[1]);
    assign C[3] = G[2] | (P[2] & C[2]);
    assign cout = G[3] | (P[3] & C[3]);

    assign sum[0] = P[0] ^ cin;
    assign sum[1] = P[1] ^ C[1];
    assign sum[2] = P[2] ^ C[2];
    assign sum[3] = P[3] ^ C[3];

endmodule
